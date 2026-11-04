"""Worker targets for process-job tests; imported by spawned worker processes."""

import os
import subprocess
import sys
import time

import numpy as np


def staged(payload, emit):
    for step in range(3):
        emit("progress", (step / 3, f"step {step}"))
        emit("partial", {"step": step})
        time.sleep(0.05)
    return {"done": payload["value"] * 2}


def failing(payload, emit):
    raise ValueError("bad input")


def sleeper_with_child(payload, emit):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    emit("partial", {"worker_pid": os.getpid(), "child_pid": child.pid})
    time.sleep(120)


def runaway(payload, emit):
    blocks = []
    emit("partial", {"worker_pid": os.getpid()})
    while True:
        # np.ones writes every page, so resident memory really grows.
        blocks.append(np.ones(4 * 1024 * 1024))
        time.sleep(0.01)
