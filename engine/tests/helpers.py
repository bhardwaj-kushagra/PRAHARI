"""Shared helpers for tests: run a configuration in memory and read the recording back."""
from prahari.core.pipeline import Simulation
from prahari.record.reader import read_recording
from prahari.record.writer import RecordingWriter


def run_cfg(cfg, path):
    sim = Simulation(cfg)
    health = sim.run(RecordingWriter(path))
    return sim, health, read_recording(path)
