from __future__ import annotations
from pathlib import Path
import yaml
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("MAMBAFLOW_DATA_DIR", Path.home() / "Library/Application Support/MambaFlow"))
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yml"
LOGS_DIR = DATA_DIR / "logs"
LOG_FILE = LOGS_DIR / "app.log"

def ensure_dirs() -> None:
    (Path.home() / "Downloads" / "MambaFlow" / "audio").mkdir(parents=True, exist_ok=True)
    (Path.home() / "Downloads" / "MambaFlow" / "video").mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)

def load_config() -> Dict[str, Any]:
    ensure_dirs()
    cfg: Dict[str, Any] = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    root = Path(os.environ.get("MAMBAFLOW_DOWNLOAD_DIR") or cfg.get("download_root") or str(Path.home() / "Downloads/MambaFlow")).expanduser().resolve()
    cfg["download_root"] = str(root)
    root.mkdir(parents=True, exist_ok=True)
    cfg["history_path"] = str(LOGS_DIR / "history.json")
    cfg["concurrency"] = max(1, min(4, int(cfg.get("concurrency", 2))))
    # cookies por defecto si existe el archivo local
    cookies_file = PROJECT_ROOT / "config" / "cookies.txt"
    if cookies_file.exists() and not cfg.get("cookies_path"):
        cfg["cookies_path"] = str(cookies_file.resolve())
    return cfg

_LOGGER: Optional[logging.Logger] = None

def get_logger(name: str = "blackmamba_ytdlp") -> logging.Logger:
    global _LOGGER
    if _LOGGER:
        return _LOGGER
    ensure_dirs()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    _LOGGER = logger
    return logger

_MANAGER = None

def get_manager():
    global _MANAGER
    if _MANAGER is None:
        from .downloader.manager import DownloadManager
        cfg = load_config()
        log = get_logger()
        _MANAGER = DownloadManager(cfg, log)
    return _MANAGER
