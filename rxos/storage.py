import json
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".rxos"
DATA_FILE = DATA_DIR / "data.json"

_cache: dict = {}

def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load() -> dict:
    global _cache
    _ensure_dir()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            _cache = {}
    else:
        _cache = {}
    return _cache

def _save():
    _ensure_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, indent=2, ensure_ascii=False, default=str)

def get(key: str, default=None):
    if not _cache:
        _load()
    return _cache.get(key, default)

def set(key: str, value):
    if not _cache and DATA_FILE.exists():
        _load()
    _cache[key] = value
    _save()

def update(key: str, value):
    set(key, value)

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# Init on import
_load()
