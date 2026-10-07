"""Seed-file archives for later analysis (protocol R4 §8): the per-seed result files of a round's stage, packed into one
byte-reproducible .tar.gz under results/research/ so they survive the run container. Sorted names, fixed modes and
owners, mtime 0 in both the tar headers and the gzip header: the same files always give the same bytes."""
from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path


def archive_seeds(out: Path, round_name: str, stage: str) -> Path:
    """Pack results/research/<round>/<stage>/<scenario>/seed*.json into <round>_seeds_<stage>.tar.gz."""
    out = Path(out)
    root = out / round_name / stage
    files = sorted(p for p in root.glob("*/seed*.json"))
    if not files:
        raise FileNotFoundError(f"no seed files under {root}")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in files:
            data = p.read_bytes()
            info = tarfile.TarInfo(name=str(p.relative_to(out)))
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    dest = out / f"{round_name}_seeds_{stage}.tar.gz"
    with open(dest, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
        gz.write(buf.getvalue())
    return dest


def extract_seeds(archive: Path, out: Path) -> list[str]:
    """Unpack an archive made by `archive_seeds` under `out` (refusing paths that leave it)."""
    out = Path(out).resolve()
    with tarfile.open(archive, "r:gz") as tar:
        names = []
        for m in tar.getmembers():
            dest = (out / m.name).resolve()
            if not str(dest).startswith(str(out)) or not m.isfile():
                raise ValueError(f"unsafe member {m.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(tar.extractfile(m).read())
            names.append(m.name)
    return names
