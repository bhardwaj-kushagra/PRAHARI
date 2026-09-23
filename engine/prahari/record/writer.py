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
from pathlib import Path


def _dumps(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), allow_nan=False, ensure_ascii=False)


class RecordingWriter:
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
            with open(self.path, "wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
                    gz.write(data)
        else:
            self.path.write_bytes(data)
