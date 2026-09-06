from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from pathlib import Path
import yt_dlp
import subprocess
import sys
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, quote
from fastapi import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from shared.security import contained_file
from shared.search import search_youtube
from shared.library import media_items, video_id

from shared import get_manager, load_config

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@asynccontextmanager
async def lifespan(app):
    manager = get_manager()
    manager.start()
    media_dir = Path(load_config()["download_root"])
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, "name", None) != "media"]
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")
    yield
    manager.stop_event.set()
    for event in manager.running.values():
        event.set()

app = FastAPI(title="Descargas yt-dlp (WebUI)", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

@app.middleware("http")
async def local_boundary(request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != str(request.base_url).rstrip("/")):
            return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

@app.get("/health")
def health():
    import shutil
    return {"app": "MambaFlow", "version": "0.2.0", "ffmpeg": bool(shutil.which("ffmpeg"))}

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    manager = get_manager()
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "jobs": manager.list_jobs()})

@app.post("/jobs")
async def create_job(request: Request, urls: str = Form(...), mode: str = Form("video")):
    manager = get_manager()
    url_list = [u.strip() for u in urls.replace("\r\n"," ").replace("\n"," ").split(" ") if u.strip()]
    try:
        job = manager.add_job(url_list, mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if "application/json" in request.headers.get("accept", ""):
        return {"id": job.id, "status": job.status.value, "message": job.message or "Añadido a la cola."}
    return RedirectResponse("/", status_code=303)

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_partial(request: Request):
    manager = get_manager()
    return templates.TemplateResponse(request=request, name="queue.html", context={"request": request, "jobs": manager.list_jobs()})

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    manager = get_manager()
    return templates.TemplateResponse(request=request, name="history.html", context={"request": request, "history": manager.get_history(), "download_root": load_config()["download_root"] + "/"})

@app.get("/history_recent", response_class=HTMLResponse)
async def history_recent(request: Request, limit: int = Query(10, ge=1, le=100)):
    manager = get_manager()
    hist = manager.get_history() or []
    items = list(reversed(hist[-limit:])) if hist else []
    return templates.TemplateResponse(request=request, name="history_recent.html", context={"request": request, "items": items})

@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = Query("", max_length=200) ):
    q = (q or "").strip()
    results = []
    artists = []
    error = None
    if q:
        try:
            results = search_youtube(q)
        except Exception:
            error = "No se pudo consultar YouTube. Revisa tu conexión y vuelve a intentar."
    return templates.TemplateResponse(request=request, name="search.html", context={"request": request, "q": q, "results": results, "artists": artists, "error": error})

@app.get("/play", response_class=HTMLResponse)
async def play(request: Request, rel: str = Query("")):
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    rel_path = Path(rel)
    file_path = (root / rel_path).resolve()
    # Seguridad: evitar traversal y exigir existencia
    if not file_path.is_relative_to(root) or not file_path.is_file():
        return HTMLResponse("Archivo no disponible", status_code=404)
    ext = file_path.suffix.lower().lstrip(".")
    is_audio = ext in ["mp3","m4a","aac","opus","ogg","wav","flac"]
    is_video = ext in ["mp4","mkv","webm","mov"]
    file_url = "/media/" + quote(rel_path.as_posix())
    return templates.TemplateResponse(request=request, name="play.html", context={"request": request, "file_url": file_url, "file_name": file_path.name, "is_audio": is_audio, "is_video": is_video})

@app.get("/videos", response_class=HTMLResponse)
async def videos(request: Request):
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    video_dir = (root / "video")
    patterns = ["*.mp4", "*.mkv", "*.webm", "*.mov"]
    items = []
    if video_dir.exists():
        for pat in patterns:
            for p in video_dir.rglob(pat):
                try:
                    rel = p.resolve().relative_to(root)
                except Exception:
                    continue
                items.append({
                    "name": p.name,
                    "rel": rel.as_posix(),
                    "url": "/media/" + quote(rel.as_posix()),
                    "size": p.stat().st_size,
                    "mtime": p.stat().st_mtime,
                })
    # ordenar por fecha reciente
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return templates.TemplateResponse(request=request, name="videos.html", context={"request": request, "items": items})

@app.get("/meta_for")
async def meta_for(rel: str = Query("")):
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    rel = (rel or "").strip()
    if not rel:
        return JSONResponse({"found": False})
    # Buscar en historial por coincidencia de ruta relativa
    mgr = get_manager()
    history = mgr.get_history() or []
    found = None
    for item in history:
        for p in (item.get("output_paths") or []):
            try:
                abs_p = Path(p).resolve()
                rel_p = abs_p.relative_to(root).as_posix()
            except Exception:
                continue
            if rel_p == rel:
                found = item
                break
        if found:
            break
    if not found:
        return JSONResponse({"found": False})
    # Construir respuesta con campos útiles
    title = None
    uploader = None
    duration = None
    # Intentar extraer de nombre
    try:
        title = Path(found["output_paths"][0]).stem
    except Exception:
        title = None
    data = {
        "found": True,
        "id": found.get("id"),
        "mode": found.get("mode"),
        "status": found.get("status"),
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "created_at": found.get("created_at"),
        "finished_at": found.get("finished_at"),
        "rel": rel,
    }
    return JSONResponse(data)

@app.get("/last_media")
async def last_media():
    """Devuelve el último medio completado del historial (prefiere video)."""
    mgr = get_manager()
    history = mgr.get_history() or []
    if not history:
        return JSONResponse({"found": False})
    # recorrer desde el final
    video_ext = {".mp4",".mkv",".webm",".mov"}
    audio_ext = {".mp3",".m4a",".aac",".opus",".ogg",".wav",".flac"}
    last_video = None
    last_audio = None
    for item in reversed(history):
        for p in (item.get("output_paths") or []):
            ext = Path(p).suffix.lower()
            if not last_video and ext in video_ext:
                last_video = (item, p)
            if not last_audio and ext in audio_ext:
                last_audio = (item, p)
        if last_video and last_audio:
            break
    chosen = last_video or last_audio
    if not chosen:
        return JSONResponse({"found": False})
    item, path = chosen
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    try:
        rel = Path(path).resolve().relative_to(root).as_posix()
    except Exception:
        rel = None
    kind = "video" if Path(path).suffix.lower() in video_ext else "audio"
    title = Path(path).stem
    return JSONResponse({"found": True, "rel": rel, "title": title, "kind": kind})

@app.post("/reveal")
async def reveal(rel: str = Form(...)):
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    file_path = (root / rel).resolve()
    if not file_path.is_relative_to(root) or not file_path.is_file():
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", "-R", str(file_path)], check=False)
            return JSONResponse({"ok": True})
        except Exception:
            return JSONResponse({"ok": False}, status_code=500)
    return JSONResponse({"ok": False, "error": "unsupported"}, status_code=400)

@app.post("/open_folder")
async def open_folder(rel: str = Form("")):
    cfg = load_config()
    root = Path(cfg.get("download_root", ".")).resolve()
    target = root if not rel else (root / rel).resolve().parent
    if not target.is_relative_to(root) or not target.is_dir():
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    if sys.platform == "darwin":
        try:
            subprocess.run(["open", str(target)], check=False)
            return JSONResponse({"ok": True})
        except Exception:
            return JSONResponse({"ok": False}, status_code=500)
    return JSONResponse({"ok": False, "error": "unsupported"}, status_code=400)

@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    if not get_manager().cancel(job_id):
        raise HTTPException(404, "Trabajo no disponible")
    return {"ok": True}

@app.get("/library", response_class=HTMLResponse)
def library(request: Request):
    root = Path(load_config()["download_root"]).resolve()
    items = []
    for path in (root / "audio").glob("*"):
        if path.is_file() and path.resolve().is_relative_to(root) and path.suffix.lower() in {".mp3", ".m4a", ".wav", ".flac", ".opus", ".ogg"}:
            rel = path.relative_to(root).as_posix()
            items.append({"name": path.stem, "rel": rel, "url": "/media/" + quote(rel), "mtime": path.stat().st_mtime})
    items.sort(key=lambda item: item["mtime"], reverse=True)
    return templates.TemplateResponse(request=request, name="library.html", context={"items": items})

@app.get("/collection", response_class=HTMLResponse)
def collection_partial(request: Request):
    manager = get_manager()
    busy = {(job.mode.value, video_id(url)) for job in manager.list_jobs() if job.status.value in ("queued", "running") for url in job.urls}
    items = [item for item in media_items(load_config()["download_root"]) if (item["mode"], item["video_id"]) not in busy]
    return templates.TemplateResponse(request=request, name="collection.html", context={"items": items})
