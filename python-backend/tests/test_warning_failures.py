"""Scientific advisories remain available when the calculation itself fails."""

import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from services.analysis_helpers import collect_warnings


def test_warning_capture_preserves_advisories_and_original_exception():
    sink = ["already present"]
    failure = ValueError("calculation failed")
    with pytest.raises(ValueError) as caught:
        with collect_warnings(sink):
            warnings.warn("low signal", UserWarning)
            warnings.warn("low signal", UserWarning)
            warnings.warn("already present", UserWarning)
            raise failure
    assert caught.value is failure
    assert sink == ["already present", "low signal"]


def test_nested_failure_preserves_each_capture_and_releases_the_lock():
    outer, inner, later = [], [], []
    with pytest.raises(RuntimeError, match="failed inside"):
        with collect_warnings(outer):
            warnings.warn("outer advisory", UserWarning)
            with collect_warnings(inner):
                warnings.warn("inner advisory", UserWarning)
                raise RuntimeError("failed inside")
    assert outer == ["outer advisory"]
    assert inner == ["inner advisory"]
    with collect_warnings(later):
        warnings.warn("later advisory", UserWarning)
    assert later == ["later advisory"]


@pytest.mark.parametrize(
    "context_aware", [False, True], ids=["fallback", "context-aware"]
)
def test_failed_capture_with_production_log_hook_in_both_warning_modes(context_aware):
    if context_aware and not hasattr(sys.flags, "context_aware_warnings"):
        pytest.skip("interpreter has no context-aware warnings mode")
    backend = str(Path(__file__).resolve().parents[1])
    script = f"""
import logging, sys, warnings
sys.path.insert(0, {backend!r})
from services import analysis_helpers
from services.analysis_helpers import collect_warnings
from utils.log_stream import log_stream_manager
assert analysis_helpers.CONTEXT_AWARE_WARNINGS is {context_aware!r}
log_stream_manager.install(log_level=logging.CRITICAL)
original_hook = warnings.showwarning
sink = []
failure = ValueError('numerical failure')
try:
    with collect_warnings(sink):
        warnings.warn('scientific advisory before failure', UserWarning)
        raise failure
except ValueError as caught:
    assert caught is failure
else:
    raise AssertionError('calculation exception was suppressed')
assert sink == ['scientific advisory before failure'], sink
assert warnings.showwarning is original_hook
later = []
with collect_warnings(later):
    warnings.warn('subsequent advisory', UserWarning)
assert later == ['subsequent advisory'], later
print('OK')
"""
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            f"context_aware_warnings={int(context_aware)}",
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
