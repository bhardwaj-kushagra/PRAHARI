"""Configuration loader (SPEC §4.3).

`configs/default.yaml` is both the defaults and the schema: a regime or scenario
file may only override keys that exist in the defaults, with a compatible type.
Unknown keys are errors naming the full key path. Every parameter block carries
a `source` whose first word is a provenance tag (CLAUDE.md rule 9).
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

TAGS = ("LIT", "VEN", "DER", "ASM", "TGT")
SOURCED_SECTIONS = ("params", "world")


class ConfigError(ValueError):
    """The configuration is invalid; the message names the bad key."""


def _read(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except OSError as exc:                                  # a directory, no permission, …
        raise ConfigError(f"cannot read {path}: {exc.strerror or exc}") from None
    except yaml.YAMLError as exc:
        where = getattr(exc, "problem_mark", None)
        at = f" (line {where.line + 1})" if where is not None else ""
        raise ConfigError(f"{path}: not valid YAML{at}") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def _compatible(default, value) -> bool:
    if default is None or value is None:
        return True
    if isinstance(default, bool) or isinstance(value, bool):
        return isinstance(default, bool) and isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float))
    return isinstance(value, type(default))


def merge(base: dict, override: dict, where: str, path: str = "") -> dict:
    """Return `base` updated by `override`; reject keys or types the defaults do not define."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        full = f"{path}.{key}" if path else str(key)
        if key not in base:
            raise ConfigError(f"{where}: unknown key '{full}'")
        if isinstance(base[key], dict) and isinstance(value, dict):
            out[key] = merge(base[key], value, where, full)
        elif not _compatible(base[key], value):
            raise ConfigError(f"{where}: key '{full}' expects {type(base[key]).__name__}, got {type(value).__name__}")
        else:
            out[key] = copy.deepcopy(value)
    return out


def check_sources(cfg: dict) -> None:
    """Every parameter block (and `world`) must carry a `source` starting with a provenance tag (rule 9)."""
    for section in SOURCED_SECTIONS:
        blocks = cfg.get(section, {})
        if section == "world":
            blocks = {"world": blocks}
        for name, block in blocks.items():
            if not isinstance(block, dict):
                raise ConfigError(f"{section}.{name}: must be a mapping")
            src = block.get("source")
            key = name if section == "world" else f"{section}.{name}"
            if not isinstance(src, str) or not src.strip():
                raise ConfigError(f"{key}: missing 'source' (one of {TAGS} plus reference)")
            if src.split(";")[0].split(",")[0].split()[0] not in TAGS:
                raise ConfigError(f"{key}.source: must start with one of {TAGS}, got {src!r}")


def check_modules(cfg: dict) -> None:
    """Every module state must be real, stub or off (rule 2)."""
    for name, state in cfg.get("modules", {}).items():
        if state not in ("real", "stub", "off"):
            raise ConfigError(f"modules.{name}: must be real, stub or off, got {state!r}")


LAYOUTS = ("grid", "corridor", "greedy")


def _number(cfg: dict, key: str, lo: float, strict: bool = True, integer: bool = False):
    section, name = key.split(".")
    v = cfg.get(section, {}).get(name)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (integer and float(v) != int(v)):
        raise ConfigError(f"{key}: expects a {'whole ' if integer else ''}number, got {v!r}")
    if (v <= lo) if strict else (v < lo):
        raise ConfigError(f"{key}: must be {'>' if strict else '≥'} {lo:g}, got {v!r}")
    return v


def check_values(cfg: dict) -> None:
    """Reject run and world values the simulator cannot run with, with a message naming the key (release 1.0).
    Checks only: no default changes, and every shipped configuration passes."""
    days = _number(cfg, "run.days", 0.0)
    _number(cfg, "run.tick_minutes", 1, strict=False, integer=True)
    n = _number(cfg, "world.n_nodes", 1, strict=False, integer=True)
    _number(cfg, "world.spacing_m", 0.0)
    _number(cfg, "record.every_k_ticks", 1, strict=False, integer=True)
    layout = cfg.get("world", {}).get("layout")
    if layout is not None and layout not in LAYOUTS:
        raise ConfigError(f"world.layout: must be one of {LAYOUTS}, got {layout!r}")
    if layout == "grid" and n is not None and round(int(n) ** 0.5) ** 2 != int(n):   # M1 — a square grid
        raise ConfigError(f"world.n_nodes: the grid layout needs a square number of nodes, got {n}")
    start = _number(cfg, "record.from_day", 0.0, strict=False)
    if days is not None and start is not None and start >= days:
        raise ConfigError(f"record.from_day: {start:g} is not inside the run of {days:g} days")


def find_default(path: Path) -> Path:
    """Locate default.yaml in the file's directory or a parent directory."""
    for d in [path.parent, *path.parents]:
        cand = d / "default.yaml"
        if cand.is_file():
            return cand
    raise ConfigError(f"no default.yaml found above {path}")


def load_config(path: str | Path, overrides: dict | None = None) -> dict:
    """Compose default.yaml, then the regime card named by the scenario, then the scenario."""
    path = Path(path).resolve()
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    default_path = find_default(path)
    cfg = _read(default_path)
    check_sources(cfg)
    if path != default_path:
        scen = _read(path)
        regime = scen.get("regime") or cfg.get("regime")
        if regime:
            rpath = default_path.parent / "regimes" / f"{regime}.yaml"
            cfg = merge(cfg, _read(rpath), str(rpath))
        cfg = merge(cfg, scen, str(path))
    if overrides:
        cfg = merge(cfg, overrides, "overrides")
    check_sources(cfg)
    check_modules(cfg)
    check_values(cfg)
    return cfg
