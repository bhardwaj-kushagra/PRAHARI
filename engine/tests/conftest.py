from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SMOKE = REPO / "configs" / "scenarios" / "smoke.yaml"


@pytest.fixture
def smoke_cfg():
    from prahari.core.config import load_config
    return load_config(SMOKE)
