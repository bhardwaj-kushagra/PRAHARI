"""R2-10: the inside/outside-haze decomposition helpers. `incident_list` must count exactly as M46's `incidents`."""
import numpy as np

from prahari.eval.stats import incidents
from prahari.research.hazesplit import active_mask, episodes, fire_overlaps, incident_list


def test_incident_list_counts_as_m46_on_random_alarms():
    rng = np.random.default_rng(7)
    xy = rng.uniform(0, 700, (40, 2))
    dist = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    for _ in range(50):
        n = int(rng.integers(0, 60))
        ts = np.sort(rng.integers(0, 3000, n))
        alarms = [(int(t), int(i), [int(i), int(j)]) for t, i, j in zip(ts, rng.integers(0, 40, n), rng.integers(0, 40, n))]
        inc = incident_list(alarms, dist, 112.0, 500, 2800)
        assert len(inc) == incidents(alarms, dist, 112.0, 500, 2800)
        assert all(a[0] <= a[1] for a in inc) and [a[0] for a in inc] == sorted(a[0] for a in inc)


def test_episodes_and_masks():
    level = np.array([0, 0, 0.5, 1.0, 0.2, 0, 0, 2.0, 0])
    eps = episodes(level)
    assert eps == [[2, 5, 1.0], [7, 8, 2.0]]
    assert active_mask(eps, 9).tolist() == [False, False, True, True, True, False, False, True, False]
    assert active_mask(eps, 9, pad=1).tolist() == [False, False, True, True, True, True, False, True, True]
    assert episodes(np.zeros(5)) == []
    assert fire_overlaps(eps, [(0, None), (5, None), (6, None)], 9, window=2) == [False, False, True]
