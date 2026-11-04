"""Run long analyses in a separate worker process.

Workers always use the ``spawn`` start method, the only one available on
Windows and the safe default on macOS: the backend runs threads, which
``fork`` would copy in an undefined state. A worker target is a top-level
function named as ``"module:function"``; it receives its payload and an
``emit(kind, data)`` callback for ``"progress"`` ((fraction, message)) and
``"partial"`` (a JSON-safe preview) messages, and returns its result.

The parent polls the worker. Cancelling terminates the worker and every
process it started. A watchdog on the resident memory of the worker tree
enforces the memory cap on every platform; Linux additionally applies an
address-space limit inside the worker.
"""

import importlib
import multiprocessing
import os
import queue as queue_module
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import psutil

CONTEXT = multiprocessing.get_context("spawn")
DEFAULT_MEMORY_FRACTION = 0.75
POLL_SECONDS = 0.05


def default_memory_cap_bytes() -> int:
    """STINGRAY_JOB_MEMORY_CAP_MB, else three quarters of physical memory."""
    configured = os.environ.get("STINGRAY_JOB_MEMORY_CAP_MB")
    if configured:
        return int(float(configured) * 1024**2)
    return int(psutil.virtual_memory().total * DEFAULT_MEMORY_FRACTION)


@dataclass
class ProcessJobOutcome:
    #: completed, failed, cancelled or memory_exceeded
    status: str
    result: Any = None
    error: Optional[str] = None
    partials: List[Any] = field(default_factory=list)
    worker_pid: Optional[int] = None


def _limit_address_space(memory_cap_bytes):
    if not sys.platform.startswith("linux") or not memory_cap_bytes:
        return
    try:
        import resource

        # Address space exceeds resident memory, so leave the RSS watchdog
        # to enforce the exact cap; this only stops a runaway allocation.
        limit = int(memory_cap_bytes * 4)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, ValueError, OSError):
        pass


def _worker(target, payload, messages, memory_cap_bytes):
    _limit_address_space(memory_cap_bytes)

    def emit(kind, data):
        messages.put((kind, data))

    try:
        module_name, function_name = target.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        messages.put(("result", function(payload, emit)))
    except BaseException as error:  # report every failure to the parent
        messages.put(("error", f"{type(error).__name__}: {error}"))


def _tree(pid):
    try:
        root = psutil.Process(pid)
        return [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []


def _resident_bytes(pid):
    total = 0
    for process in _tree(pid):
        try:
            total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


def _kill_tree(process):
    """Terminate the worker and everything it started; leave no orphans."""
    members = _tree(process.pid) if process.pid is not None else []
    for member in reversed(members):
        try:
            member.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(members, timeout=3)
    for member in alive:
        try:
            member.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(alive, timeout=3)
    process.join(timeout=3)


def run_process_job(
    target: str,
    payload: Any,
    *,
    on_progress: Optional[Callable[[float, str], None]] = None,
    on_partial: Optional[Callable[[Any], None]] = None,
    should_cancel: Callable[[], bool] = lambda: False,
    memory_cap_bytes: Optional[int] = None,
) -> ProcessJobOutcome:
    """Run ``target`` in a spawned worker and report how it ended."""
    cap = default_memory_cap_bytes() if memory_cap_bytes is None else memory_cap_bytes
    messages = CONTEXT.Queue()
    worker = CONTEXT.Process(
        target=_worker,
        args=(target, payload, messages, cap),
        daemon=True,
        name="stingray-analysis",
    )
    worker.start()
    outcome: Optional[ProcessJobOutcome] = None
    partials: List[Any] = []
    try:
        while outcome is None:
            try:
                kind, data = messages.get(timeout=POLL_SECONDS)
            except queue_module.Empty:
                kind = None
            if kind == "progress":
                if on_progress is not None:
                    on_progress(float(data[0]), str(data[1]))
            elif kind == "partial":
                partials.append(data)
                if on_partial is not None:
                    on_partial(data)
            elif kind == "result":
                outcome = ProcessJobOutcome("completed", result=data)
            elif kind == "error":
                outcome = ProcessJobOutcome("failed", error=data)
            if outcome is not None:
                break
            if should_cancel():
                _kill_tree(worker)
                outcome = ProcessJobOutcome("cancelled", error="Cancelled")
            elif cap and _resident_bytes(worker.pid) > cap:
                _kill_tree(worker)
                outcome = ProcessJobOutcome(
                    "memory_exceeded",
                    error=(
                        f"The analysis exceeded the {cap / 1024**2:.0f} MB memory cap "
                        "and was stopped; use a coarser time bin, a shorter segment "
                        "or a smaller input"
                    ),
                )
            elif not worker.is_alive() and messages.empty():
                outcome = ProcessJobOutcome(
                    "failed",
                    error=f"The analysis worker exited unexpectedly (code {worker.exitcode})",
                )
    finally:
        if worker.is_alive():
            worker.join(timeout=5)
        if worker.is_alive():
            _kill_tree(worker)
        messages.close()
        messages.join_thread()
    outcome.partials = partials
    outcome.worker_pid = worker.pid
    return outcome
