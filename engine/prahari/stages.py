"""Import every stage module so that its implementations register themselves."""
from prahari.comms import lorawan, lorawan_real, pathloss  # noqa: F401
from prahari.detect.baselines import fixed, v1, v1t  # noqa: F401
from prahari.detect.prahari import cluster, cusum, escalate, fisher, learn, qcc, raq, scmr, score, srp, ttc  # noqa: F401
from prahari.detect.prahari import cusum_real, decide_real, edge_real, escalate_real, qcc_real, ttc_real  # noqa: F401
from prahari.energy import budget, budget_real  # noqa: F401
from prahari.env import ffmc, weather  # noqa: F401
from prahari.fire import gaussian, growth, ignition, plume  # noqa: F401
from prahari.satellite import overpass  # noqa: F401
from prahari.sensors import faults, haze, mox, nuisance  # noqa: F401
from prahari.world import landscape, siting  # noqa: F401
