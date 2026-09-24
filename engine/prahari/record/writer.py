"""Recording writer: gzipped newline-delimited JSON (SPEC §4.6).

Line 1 is {"header": ...}; then frames (objects with "t") and {"trace": ...}
lines in time order; the last line is {"footer": ...}. Output is byte-identical
for the same seed and configuration: fixed key order, 4-significant-figure
floats, and a gzip header with mtime 0 and no file name (DECISIONS P0-2).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import tempfile
from pathlib import Path


def write_atomic(path: str | Path, data: bytes) -> None:
    """Write `data` to `path` all at once: a temporary file in the same folder, then a rename (release 1.0). An
    interrupted or failed write leaves the previous file untouched, never a truncated one."""
    path = Path(path)
    if path.is_dir():
        raise IsADirectoryError(21, "Is a directory, not a file", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_text_atomic(path: str | Path, text: str) -> None:
    """`write_atomic` for UTF-8 text (results JSON, health files)."""
    write_atomic(path, text.encode("utf-8"))


def _dumps(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


class RecordingWriter:
    """Collects header, frames and traces in memory and writes the gzipped recording once, at `close`."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._buf = io.StringIO()
        self.n_frames = 0
        self.n_traces = 0

    def header(self, header: dict) -> None:
        self._buf.write(_dumps({"header": header}) + "\n")

    def frame(self, frame: dict) -> None:
        self._buf.write(_dumps(frame) + "\n")
        self.n_frames += 1

    def trace(self, record: dict) -> None:
        self._buf.write(_dumps({"trace": record}) + "\n")
        self.n_traces += 1

    def close(self, footer: dict) -> None:
        self._buf.write(_dumps({"footer": footer}) + "\n")
        data = self._buf.getvalue().encode("utf-8")
        if self.path.suffix == ".gz":
            raw = io.BytesIO()
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
                gz.write(data)
            data = raw.getvalue()
        write_atomic(self.path, data)
