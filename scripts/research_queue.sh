#!/usr/bin/env bash
# Research run queue (paper branch): the R1 haze-split re-run (DECISIONS R2-10), then protocol R2 — H-mix selection,
# then every scenario's test seeds. Every step resumes from its existing seed files, so the queue can be relaunched
# after a container restart. One queue at a time (flock). Logs: results/research/logs/queue.log (not committed).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results/research/logs
exec 9>results/research/logs/queue.lock
flock -n 9 || { echo "queue already running"; exit 0; }
JOBS="${JOBS:-4}"
log() { echo "$(date -u +%FT%TZ) $*" >> results/research/logs/queue.log; }
log "queue start"
python3 -c "
from pathlib import Path
from prahari.research.runner import load_r1, run_stage
run_stage(load_r1(), 'test', $JOBS, Path('results/research/r1b'))" >> results/research/logs/queue.log 2>&1
log "r1b test done"
python3 -m prahari.research r2-run selection --jobs "$JOBS" >> results/research/logs/queue.log 2>&1
log "r2 selection done"
python3 -m prahari.research r2-run test --jobs "$JOBS" >> results/research/logs/queue.log 2>&1
log "r2 test done"
log "queue finished"
