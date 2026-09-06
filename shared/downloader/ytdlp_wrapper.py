from __future__ import annotations
from typing import Callable, Dict, Any, List
from pathlib import Path
import yt_dlp
from .jobs import Job, JobMode
import threading

class Downloader:
    def __init__(self, config: Dict[str, Any], logger):
        self.cfg = config
        self.logger = logger

    def _build_common_opts(self, mode: JobMode, cancel_event: threading.Event, on_progress: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        download_root = Path(self.cfg["download_root"]).resolve()
        out_dir = download_root / ("audio" if mode == JobMode.audio else "video")
        out_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(out_dir / "%(title).180B [%(id)s].%(ext)s")
        opts: Dict[str, Any] = {
            "outtmpl": {"default": outtmpl},
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [],
            "postprocessor_hooks": [],
            "overwrites": False,
            "noplaylist": True,
            "socket_timeout": 15,
            "retries": 3,
            "fragment_retries": 3,
            "ignoreerrors": False,
        }
        if self.cfg.get("proxy"):
            opts["proxy"] = self.cfg["proxy"]
        if self.cfg.get("cookies_path"):
            opts["cookiefile"] = self.cfg["cookies_path"]
        if self.cfg.get("write_subs"):
            opts["writesubtitles"] = True

        def hook(d: Dict[str, Any]):
            if cancel_event.is_set():
                raise yt_dlp.utils.DownloadError("Cancelado por el usuario")
            try:
                on_progress(d)
            except Exception as e:
                self.logger.error(f"Error en hook de progreso: {e}")

        opts["progress_hooks"].append(hook)
        opts["postprocessor_hooks"].append(hook)
        return opts

    def _opts_for_mode(self, mode: JobMode, opts: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self.cfg
        if mode == JobMode.audio:
            opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": cfg.get("audio_format", "mp3"),
                        "preferredquality": str(cfg.get("audio_quality", "320k")).replace("k", ""),
                    }
                ],
            })
            if cfg.get("add_metadata", True):
                opts["postprocessors"].append({"key": "FFmpegMetadata"})
            if cfg.get("embed_thumbnail", False):
                opts["writethumbnail"] = True
                opts["postprocessors"].append({"key": "EmbedThumbnail"})
        else:
            opts.update({
                "format": cfg.get("video_format", "bestvideo+bestaudio/best"),
                "merge_output_format": cfg.get("merge_output_format", "mp4"),
            })
            if cfg.get("add_metadata", True):
                opts.setdefault("postprocessors", [])
                opts["postprocessors"].append({"key": "FFmpegMetadata"})
        return opts

    def download(self, job: Job, on_event: Callable[[Dict[str, Any]], None], cancel_event: threading.Event) -> List[str]:
        emitted_paths: List[str] = []

        def progress_dispatch(d: Dict[str, Any]):
            d2 = dict(d)
            d2["_job_id"] = job.id
            fn = d.get("filename") or (d.get("info_dict") or {}).get("filepath") or (d.get("info_dict") or {}).get("_filename")
            if fn:
                emitted_paths.append(str(fn))
            on_event(d2)

        opts = self._build_common_opts(job.mode, cancel_event, progress_dispatch)
        opts = self._opts_for_mode(job.mode, opts)

        ydl = yt_dlp.YoutubeDL(opts)
        results: List[str] = []
        for idx, url in enumerate(job.urls, start=1):
            job.current_index = idx - 1
            if cancel_event.is_set():
                break
            try:
                self.logger.info(f"Iniciando descarga ({idx}/{len(job.urls)}): {url}")
                info = ydl.extract_info(url, download=True)
                if "requested_downloads" in info and info["requested_downloads"]:
                    for rd in info["requested_downloads"]:
                        fp = rd.get("filepath") or rd.get("_filename") or ydl.prepare_filename(rd)
                        if fp:
                            results.append(str(fp))
                else:
                    fp = info.get("filepath") or info.get("_filename") or ydl.prepare_filename(info)
                    if fp:
                        results.append(str(fp))
            except yt_dlp.utils.DownloadError as e:
                self.logger.error(f"Error descargando {url}: {e}")
                raise
        # combinar rutas detectadas
        all_paths: List[str] = []
        seen = set()
        for p in results + emitted_paths:
            if p and p not in seen and Path(p).is_file() and Path(p).suffix.lower() in {".mp3", ".m4a", ".mp4", ".webm", ".mkv", ".opus", ".flac", ".wav"}:
                all_paths.append(p)
                seen.add(p)
        return all_paths
