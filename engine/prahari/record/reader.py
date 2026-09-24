"""Recording reader (SPEC §4.6)."""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Recording:
    header: dict
    frames: list = field(default_factory=list)
    traces: list = field(default_factory=list)
    footer: dict = field(default_factory=dict)


def read_recording(path: str | Path) -> Recording:
    path = Path(path)
    raw = path.read_bytes()
    text = (gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw).decode("utf-8")
    rec = None
    for line in text.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if "header" in obj:
            rec = Recording(header=obj["header"])
        elif rec is None:
            raise ValueError(f"{path}: first line must be the header")
        elif "trace" in obj:
            rec.traces.append(obj["trace"])
        elif "footer" in obj:
            rec.footer = obj["footer"]
        else:
            rec.frames.append(obj)
    if rec is None:
        raise ValueError(f"{path}: empty recording")
    return rec
