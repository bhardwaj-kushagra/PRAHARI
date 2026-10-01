"""Shared helpers for the real-data fetch scripts: checksummed downloads and manifests (charter rule 7)."""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def download(url: str, dest: Path, headers: dict | None = None, tries: int = 4, timeout: int = 120) -> None:
    """Download `url` to `dest` atomically, retrying with exponential backoff."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            tmp.replace(dest)
            return
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))


def update_manifest(path: Path, entries: dict, extra: dict | None = None) -> None:
    """Merge {relative file: {url, sha256, bytes, retrieved_utc}} into the manifest (sorted, stable)."""
    m = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"files": {}}
    m.update(extra or {})
    m["files"].update(entries)
    m["files"] = dict(sorted(m["files"].items()))
    path.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
