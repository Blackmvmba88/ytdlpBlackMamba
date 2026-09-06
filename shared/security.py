"""Local application input boundaries."""
from pathlib import Path
from urllib.parse import urlsplit

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}

def validate_urls(urls):
    values = list(dict.fromkeys(u.strip() for u in urls if u.strip()))
    if not 1 <= len(values) <= 20:
        raise ValueError("Introduce entre 1 y 20 enlaces de YouTube.")
    for value in values:
        parsed = urlsplit(value)
        if len(value) > 2048 or parsed.scheme != "https" or parsed.hostname not in YOUTUBE_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError("Usa enlaces HTTPS de YouTube o youtu.be.")
    return values

def contained_file(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Archivo no disponible")
    return path
