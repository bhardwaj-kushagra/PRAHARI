"""Random-number streams (SPEC §4.4, P7; CLAUDE.md rule 7).

One generator per stream, spawned from the master seed. New streams are
appended at the END of STREAMS so existing streams never change.
"""
from __future__ import annotations

import numpy as np

STREAMS = ["weather", "ignition", "growth", "plume", "sensor", "nuisance", "haze", "faults", "comms", "satellite",
           "protocol",                     # Phase 4: evaluation protocol (day types, protocol fires)
           "srp",                          # Phase 6: legacy day types (M33)
           "links", "energy"]              # Phase 8: M38 shadowing; cloudy days and canopy spread (M42)


def make_rngs(seed: int) -> dict[str, np.random.Generator]:
    """One independent generator per module stream, spawned from the master seed with SeedSequence (rule 7).
    Streams are appended at the end of STREAMS, so adding a module never changes the others' draws."""
    root = np.random.SeedSequence(seed)
    return {name: np.random.default_rng(child) for name, child in zip(STREAMS, root.spawn(len(STREAMS)))}
