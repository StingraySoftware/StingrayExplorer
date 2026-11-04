"""Independent numerical regressions for cross-version scientific adapters."""

from types import SimpleNamespace

import numpy as np
import pytest
from astropy.io import fits
from stingray import EventList
from services.scientific_compatibility import (
    averaged_raw_coherence,
    compatible_bispectrum,
    compatible_event_lightcurve,
    event_read_options,
    mask_legacy_low_count_rms,
)
from services.project_service import encode, decode
from services.io_utility_service import _table_for_object


def test_coherence_bias_uses_averages_not_time_bin_count():
    p1, p2 = np.array([100.0, 50.0]), np.array([110.0, 60.0])
    c = np.array([80 + 5j, 30 - 2j])
    spectrum = SimpleNamespace(
        m=8,
        n=128,
        nphots1=20,
        nphots2=30,
        unnorm_power=c,
        pds1=SimpleNamespace(unnorm_power=p1),
        pds2=SimpleNamespace(unnorm_power=p2),
    )
    with pytest.warns(UserWarning, match="Number of segments"):
        values, errors = averaged_raw_coherence(spectrum)
    expected = (np.abs(c) ** 2 - (p1 * p2 - (p1 - 20) * (p2 - 30)) / 8) / (p1 * p2)
    np.testing.assert_allclose(values, expected)
    np.testing.assert_allclose(
        errors, np.sqrt(2) * expected * (1 - expected) / np.sqrt(expected * 8)
    )


@pytest.mark.parametrize("requested,expected", [(0.05, 0.1), (0.18, 0.2), (0.2, 0.2)])
def test_instrument_clock_rounding_preserves_input_and_counts(requested, expected):
    events = EventList(time=np.arange(0.01, 2, 0.02), gti=[[0, 2]], dt=0.1)
    photons = events.time.copy()
    with __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        lightcurve = compatible_event_lightcurve(events, requested)
    assert lightcurve.dt == pytest.approx(expected)
    assert lightcurve.counts.sum() == len(photons)
    assert events.dt == 0.1
    np.testing.assert_array_equal(events.time, photons)


def test_old_header_commentary_is_losslessly_exportable_and_project_serializable():
    header = fits.Header()
    header["COMMENT"] = "first comment"
    header["COMMENT"] = "second comment"
    events = EventList(time=[1.0, 2.0, 3.0], gti=[[0, 4]])
    events.header = {"COMMENT": header["COMMENT"], "MISSION": "test"}
    table = _table_for_object(events, "event_list", preserve_timing_precision=True)
    assert table.meta["header"]["COMMENT"] == ["first comment", "second comment"]
    restored = decode(encode(events))
    assert restored.header["COMMENT"] == ["first comment", "second comment"]
    assert list(events.header["COMMENT"]) == ["first comment", "second comment"]


def test_complete_fits_header_cards_survive_project_codec():
    header = fits.Header()
    header["COMMENT"] = "first"
    header["COMMENT"] = "second"
    restored = decode(encode(header))
    assert restored.tostring() == header.tostring()


def test_reader_options_keep_granted_rmf_and_filter_unsupported_flags(monkeypatch):
    from services import scientific_compatibility as module

    class Reader:
        def __init__(self, filename, additional_columns=None):
            pass

    monkeypatch.setattr(module, "FITSTimeseriesReader", Reader)
    retained_stream = object()
    options = event_read_options(
        "ogip",
        rmf_file=retained_stream,
        high_precision=True,
        skip_checks=False,
        additional_columns=["PI"],
    )
    assert options == {"rmf_file": retained_stream, "additional_columns": ["PI"]}
    assert event_read_options("ascii.ecsv", high_precision=True) == {
        "high_precision": True
    }


def test_legacy_rms_policy_masks_sparse_bands_without_mutating_events():
    times = np.arange(0.25, 16, 0.5)
    events = EventList(time=times, energy=np.full(len(times), 1.0), gti=[[0, 16]])
    spectrum = SimpleNamespace(
        energy_intervals=[(0.0, 2.0), (2.0, 4.0)],
        spectrum=np.array([0.2, 0.3]),
        spectrum_error=np.array([0.1, 0.1]),
    )
    notes = []
    mask_legacy_low_count_rms(spectrum, events, 4.0, notes)
    assert np.isnan(spectrum.spectrum).all()
    assert np.isnan(spectrum.spectrum_error).all()
    assert len(notes) == 2
    np.testing.assert_array_equal(events.time, times)


@pytest.mark.parametrize("scale", [1.0, 1e150, 1e-150])
def test_lightcurve_rebin_propagates_standard_errors_without_mutating_source(scale):
    from stingray import Lightcurve
    from services.scientific_compatibility import rebin_lightcurve_with_standard_errors

    source = Lightcurve(
        np.arange(0.5, 4),
        [2.0, 3.0, 5.0, 7.0],
        err=np.full(4, 2.0 * scale),
        err_dist="gauss",
        dt=1.0,
        gti=[[0, 4]],
    )
    original = source.counts_err.copy()
    result, _ = rebin_lightcurve_with_standard_errors(source, 2.0)
    np.testing.assert_allclose(result.counts, [5.0, 12.0])
    np.testing.assert_allclose(result.counts_err / scale, np.sqrt([8.0, 8.0]))
    np.testing.assert_array_equal(source.counts_err, original)
    assert result.err_dist == "gauss"


@pytest.mark.parametrize("background", [0.0, 20.0])
def test_cached_deadtime_series_matches_upstream_without_reducing_model_order(
    background,
):
    from services.scientific_compatibility import cached_zhang_deadtime_model
    from stingray.deadtime.model import non_paralyzable_dead_time_model

    freqs = np.linspace(0.5, 10.0, 12)
    with __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        expected = non_paralyzable_dead_time_model(
            freqs, 0.0025, 100.0, bin_time=0.001, limit_k=10, background_rate=background
        )
    actual = cached_zhang_deadtime_model(freqs, 0.0025, 100.0, 0.001, 10, background)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_bispectrum_adapter_matches_flattened_upstream_computation(monkeypatch):
    import stingray
    from stingray import Lightcurve
    from stingray.bispectrum import Bispectrum

    rng = np.random.default_rng(7)
    lightcurve = Lightcurve(np.arange(256) * 0.25, rng.poisson(20, 256), dt=0.25)
    options = dict(maxlag=10, scale="unbiased", window="hamming")
    reference = compatible_bispectrum(lightcurve, **options)
    # Force the legacy rebinding path on whichever release is installed.
    monkeypatch.setattr(stingray, "__version__", "2.2")
    legacy = compatible_bispectrum(lightcurve, **options)
    assert type(legacy) is Bispectrum
    assert not {"_get_window", "_cumulant3", "_normalize_cumulant3"} & set(vars(legacy))
    np.testing.assert_allclose(legacy.cum3, reference.cum3)
    np.testing.assert_allclose(legacy.bispec_mag, reference.bispec_mag)
    np.testing.assert_allclose(legacy.bispec_phase, reference.bispec_phase)
