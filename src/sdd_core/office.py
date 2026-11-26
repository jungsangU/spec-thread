"""Read the project-local Office delegation shared with the Monitor."""
import hashlib
import json
import os
from pathlib import Path
import time

LEASE_SECONDS = 10


def location(root):
    key = hashlib.sha256(os.path.normcase(str(root.resolve())).encode("utf-8")).hexdigest()
    base = (Path(os.environ["LOCALAPPDATA"]) if os.name == "nt" and os.environ.get("LOCALAPPDATA")
            else Path.home() / ".cache")
    return base / "spec-thread" / "observations" / key


def active_role(root, role):
    if role not in ("reader", "ceo"):
        return False
    try:
        folder = location(root)
        state = folder / role
        if folder.is_symlink() or state.is_symlink() or not state.is_file() or state.stat().st_size > 64:
            return False
        expires = json.loads(state.read_text(encoding="utf-8"))
        now = time.time()
        return type(expires) in (float, int) and now < expires <= now + LEASE_SECONDS
    except (OSError, ValueError):
        return False
