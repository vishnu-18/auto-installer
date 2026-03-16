"""Configuration file manager for .mc.json files.
Password is obfuscated using base64 (not encryption, but not plain text).
"""

import base64
import json
import os

CONFIG_EXT = ".mc.json"
RECENT_STORE = os.path.join(os.path.expanduser("~"), ".auto_installer_recent.json")
MAX_RECENT = 10


def _encode_password(password: str) -> str:
    return base64.b64encode(password.encode()).decode()


def _decode_password(encoded: str) -> str:
    try:
        return base64.b64decode(encoded.encode()).decode()
    except Exception:
        return ""


def save_config(path: str, data: dict) -> None:
    """Save config to a .mc.json file. Password is base64-encoded."""
    payload = {
        "software": data.get("software", ""),
        "host": data.get("host", ""),
        "username": data.get("username", ""),
        "password_enc": _encode_password(data.get("password", "")),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    _add_recent(path)


def load_config(path: str) -> dict:
    """Load config from a .mc.json file. Returns plain dict with decoded password."""
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    _add_recent(path)
    return {
        "software": payload.get("software", ""),
        "host": payload.get("host", ""),
        "username": payload.get("username", ""),
        "password": _decode_password(payload.get("password_enc", "")),
    }


def get_recent() -> list[str]:
    """Return list of recent file paths (most recent first)."""
    if not os.path.exists(RECENT_STORE):
        return []
    try:
        with open(RECENT_STORE, "r", encoding="utf-8") as f:
            paths = json.load(f)
        # Filter out paths that no longer exist
        return [p for p in paths if os.path.exists(p)]
    except Exception:
        return []


def _add_recent(path: str) -> None:
    path = os.path.abspath(path)
    recent = get_recent()
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    recent = recent[:MAX_RECENT]
    try:
        with open(RECENT_STORE, "w", encoding="utf-8") as f:
            json.dump(recent, f, indent=2)
    except Exception:
        pass
