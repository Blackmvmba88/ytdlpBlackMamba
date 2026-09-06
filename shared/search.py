"""Bounded, serialized metadata searches with a short cache."""
import threading
import time
import yt_dlp
_cache = {}
_lock = threading.Lock()

def search_youtube(query):
    query = query.strip()[:200]
    with _lock:
        cached = _cache.get(query)
        if cached and time.monotonic() - cached[0] < 120:
            return cached[1]
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "socket_timeout": 10, "retries": 1}) as ydl:
            info = ydl.extract_info(f"ytsearch8:{query}", download=False)
        results = [{"title": e.get("title"), "uploader": e.get("uploader"), "duration": e.get("duration"), "url": "https://www.youtube.com/watch?v=" + e["id"], "thumb": (e.get("thumbnails") or [{}])[-1].get("url")} for e in (info or {}).get("entries", []) if e and e.get("id")]
        if len(_cache) >= 64:
            _cache.pop(next(iter(_cache)))
        _cache[query] = (time.monotonic(), results)
        return results
