"""Import every stage module so that its implementations register themselves."""
from prahari.comms import lorawan, pathloss  # noqa: F401
from prahari.detect.prahari import cluster, cusum, escalate, fisher, learn, qcc, raq, scmr, score, srp, ttc  # noqa: F401
from prahari.energy import budget  # noqa: F401
from prahari.env import ffmc, weather  # noqa: F401
from prahari.fire import growth, ignition, plume  # noqa: F401
from prahari.satellite import overpass  # noqa: F401
from prahari.sensors import faults, haze, mox, nuisance  # noqa: F401
from prahari.world import landscape, siting  # noqa: F401
