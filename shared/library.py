"""Disk-backed media collection, identified by YouTube ID and media mode."""
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, quote
import re

EXTENSIONS = {"audio": {".mp3", ".m4a", ".wav", ".flac", ".opus", ".ogg", ".aac"}, "video": {".mp4", ".webm", ".mkv", ".mov"}}

def video_id(url):
    parsed = urlsplit(url)
    parts = parsed.path.strip('/').split('/')
    candidate = parts[0] if parsed.hostname == 'youtu.be' else parse_qs(parsed.query).get('v', [''])[0]
    if not candidate and len(parts) > 1 and parts[0] in {'shorts', 'live', 'embed'}:
        candidate = parts[1]
    return candidate if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', candidate or '') else None

def identity(url):
    return video_id(url) or url

def media_items(root):
    root = Path(root).resolve()
    items = []
    for mode, extensions in EXTENSIONS.items():
        for path in (root / mode).glob('*'):
            try:
                if path.suffix.lower() not in extensions or not path.resolve().is_relative_to(root) or not path.is_file():
                    continue
                stat = path.stat()
                if not stat.st_size:
                    continue
                rel = path.relative_to(root).as_posix()
                match = re.search(r'\[([A-Za-z0-9_-]{1,64})\]$', path.stem)
                items.append({'name': path.stem, 'rel': rel, 'url': '/media/' + quote(rel), 'mode': mode, 'mtime': stat.st_mtime, 'size': stat.st_size, 'video_id': match[1] if match else None})
            except OSError:
                continue
    return sorted(items, key=lambda item: item['mtime'], reverse=True)

def existing_media(root, url, mode):
    vid = video_id(url)
    if not vid:
        return None
    for item in media_items(root):
        if item['mode'] == mode and item['video_id'] == vid:
            return str(Path(root).resolve() / item['rel'])
    return None
