"""Light curves read from mission FITS files through native read grants."""

import io
import json
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from services.lightcurve_files import (
    LightcurveFileError,
    describe_lightcurve_hdus,
    read_lightcurve_fits,
)
from services.lightcurve_service import LightcurveService
from services.project_service import ProjectService
from services.spectrum_service import SpectrumService
from services.state_manager import StateManager
from tests.test_io_utility_service import TEST_SECRET, make_grant

DATA = Path(__file__).resolve().parents[2] / "files" / "data"


def _write(path, rate_hdu, gti=None, gti_name="GTI"):
    hdus = [fits.PrimaryHDU(), rate_hdu]
    if gti is not None:
        gti_hdu = fits.BinTableHDU.from_columns(
            [
                fits.Column("START", "D", array=[start for start, _ in gti]),
                fits.Column("STOP", "D", array=[stop for _, stop in gti]),
            ],
            name=gti_name,
        )
        hdus.append(gti_hdu)
    fits.HDUList(hdus).writeto(path)
    return path


def _rate_hdu(columns, name="RATE", **header):
    hdu = fits.BinTableHDU.from_columns(columns, name=name)
    for key, value in header.items():
        hdu.header[key] = value
    return hdu


def nicer_like(path):
    """Absolute TIME in s, MJDREFI/F, FRACEXP and a GTI extension."""
    time = 300000000.0 + np.arange(100) * 1.0 + 0.5
    rate = np.full(100, 20.0)
    fracexp = np.ones(100)
    fracexp[10] = 0.5
    columns = [
        fits.Column("TIME", "D", array=time),
        fits.Column("RATE", "E", array=rate),
        fits.Column("ERROR", "E", array=np.full(100, 4.0)),
        fits.Column("FRACEXP", "E", array=fracexp),
    ]
    hdu = _rate_hdu(
        columns,
        TELESCOP="NICER",
        INSTRUME="XTI",
        TIMEUNIT="s",
        TIMESYS="TT",
        MJDREFI=56658,
        MJDREFF=0.000777592592592593,
        TIMEZERO=-1.0,
        TSTART=300000000.0,
        TSTOP=300000100.0,
        TIMEDEL=1.0,
    )
    return _write(path, hdu, gti=[(300000000.0 - 1.0, 300000100.0 - 1.0)])


def swift_like(path):
    """MJDREF as one float and a 2 s bin width."""
    time = 600000000.0 + np.arange(50) * 2.0 + 1.0
    columns = [
        fits.Column("TIME", "D", array=time),
        fits.Column("RATE", "E", array=np.full(50, 3.0)),
        fits.Column("ERROR", "E", array=np.full(50, 0.5)),
    ]
    hdu = _rate_hdu(
        columns,
        TELESCOP="SWIFT",
        INSTRUME="XRT",
        TIMEUNIT="s",
        MJDREF=51910.00074287037,
        TSTART=600000000.0,
        TSTOP=600000100.0,
        TIMEDEL=2.0,
    )
    return _write(path, hdu, gti=[(600000000.0, 600000100.0)])


def rxte_like(path):
    """RXTE PCA style: STDGTI extension, MJDREFI/F, non-zero TIMEZERO."""
    time = 150000000.0 + np.arange(64) * 0.125
    columns = [
        fits.Column("TIME", "D", array=time),
        fits.Column("RATE", "E", array=np.full(64, 400.0)),
        fits.Column("ERROR", "E", array=np.full(64, 56.0)),
    ]
    hdu = _rate_hdu(
        columns,
        TELESCOP="XTE",
        INSTRUME="PCA",
        TIMEUNIT="s",
        MJDREFI=49353,
        MJDREFF=0.000696574074,
        TIMEZERO=3.378431,
        TSTART=150000000.0,
        TSTOP=150000008.0,
        TIMEDEL=0.125,
    )
    return _write(path, hdu, gti=[(150000000.0, 150000008.0)], gti_name="STDGTI")


def generic_counts(path, **header):
    """A bare COUNTS table: no TIMEUNIT, TSTART or GTI extension."""
    columns = [
        fits.Column("TIME", "D", array=np.arange(20) * 10.0),
        fits.Column("COUNTS", "J", array=np.arange(20) % 5),
    ]
    return _write(path, _rate_hdu(columns, name="LIGHTCURVE", **header))


def multiband(path):
    """eROSITA-style RATE column with one value per energy band."""
    rate = np.column_stack([np.full(30, 1.0), np.full(30, 2.0), np.full(30, 3.0)])
    columns = [
        fits.Column("TIME", "D", array=626421689.3 + np.arange(30) * 100.0),
        fits.Column("RATE", "3E", array=rate),
        fits.Column("RATE_ERR", "3E", array=rate / 10),
    ]
    hdu = _rate_hdu(
        columns,
        TELESCOP="eROSITA",
        TIMEUNIT="s",
        MJDREF=51543.875,
        TSTART=626421689.3,
        TSTOP=626424689.3,
        TIMEDEL=100.0,
        TIMESYS="TT",
    )
    return _write(path, hdu)


def _read(path, **options):
    with open(path, "rb") as stream:
        return read_lightcurve_fits(stream, **options)


# --- reading -------------------------------------------------------------


def test_nicer_like_file_respects_mjdref_timezero_fracexp_and_gtis(tmp_path):
    lc, provenance, _warnings = _read(nicer_like(tmp_path / "nicer.lc"))
    assert lc.mjdref == pytest.approx(56658.000777592592592593)
    assert float(lc.time[0]) == pytest.approx(300000000.5 - 1.0)
    assert lc.dt == 1.0
    np.testing.assert_allclose(np.asarray(lc.gti, dtype=float), [[299999999.0, 300000099.0]])
    assert lc.counts[0] == pytest.approx(20.0)
    assert lc.counts_err[0] == pytest.approx(4.0)
    assert lc.counts[10] == pytest.approx(0.0)  # FRACEXP below the 0.9 limit
    assert provenance["reader"] == "stingray.io.lcurve_from_fits"
    assert provenance["hdu"] == {"index": 1, "name": "RATE"}
    assert provenance["rate_column"] == "RATE"
    assert provenance["telescope"] == "NICER"
    assert provenance["mjdref_source"] == "header"


def test_swift_like_file_uses_float_mjdref_and_bin_width(tmp_path):
    lc, provenance, _ = _read(swift_like(tmp_path / "xrt.lc"))
    assert lc.mjdref == pytest.approx(51910.00074287037)
    assert lc.dt == 2.0
    assert lc.counts[0] == pytest.approx(6.0)
    assert lc.counts_err[0] == pytest.approx(1.0)
    assert provenance["instrument"] == "XRT"


def test_rxte_like_file_reads_the_stdgti_extension(tmp_path):
    lc, provenance, _ = _read(rxte_like(tmp_path / "pca.lc"))
    np.testing.assert_allclose(np.asarray(lc.gti, dtype=float), [[150000000.0, 150000008.0]])
    assert float(lc.time[0]) == pytest.approx(150000000.0 + 3.378431)
    assert lc.counts[0] == pytest.approx(50.0)
    assert provenance["gti_extension"] == "STDGTI"


def test_generic_counts_table_needs_a_reference_epoch(tmp_path):
    path = generic_counts(tmp_path / "plain.fits")
    with pytest.raises(LightcurveFileError, match="MJDREF"):
        _read(path)
    lc, provenance, _ = _read(path, mjdref=58000.0)
    assert lc.mjdref == 58000.0
    assert provenance["mjdref_source"] == "request"
    assert provenance["reader"] == "application_ogip"
    assert lc.dt == 10.0
    assert lc.err_dist == "poisson"
    np.testing.assert_array_equal(lc.counts, np.arange(20) % 5)


def test_relative_time_files_use_a_zero_epoch(tmp_path):
    lc, provenance, _ = _read(generic_counts(tmp_path / "rel.fits", TIMESYS="RELATIVE"))
    assert lc.mjdref == 0
    assert provenance["mjdref_source"] == "relative_time"


def test_multiband_rate_columns_need_a_band(tmp_path):
    path = multiband(tmp_path / "erosita.fits")
    with pytest.raises(LightcurveFileError, match="3 energy bands"):
        _read(path)
    lc, provenance, _ = _read(path, band=2)
    assert lc.counts[0] == pytest.approx(300.0)
    assert lc.counts_err[0] == pytest.approx(30.0)
    assert provenance["band"] == 2
    assert provenance["reader"] == "application_ogip"


def test_repository_light_curve_in_days_matches_stingray():
    # XRONOS output: TSTART/TIMEZERO are absolute days, so Stingray derives
    # seconds from its reference epoch without guessing the absolute time.
    lc, provenance, _ = _read(DATA / "lcurveA.fits")
    assert len(lc.time) == 1026
    assert lc.dt == pytest.approx(1.0)
    assert float(np.sum(lc.counts)) == pytest.approx(1000.0, rel=1e-6)
    assert lc.mjdref == pytest.approx(55197.00076601852)
    assert provenance["timeunit"] == "d"
    assert provenance["mjdref_source"] == "absolute_days"
    assert provenance["reader"] == "stingray.io.lcurve_from_fits"


def test_hdu_choices_are_described(tmp_path):
    with fits.open(multiband(tmp_path / "erosita.fits")) as hdul:
        described = describe_lightcurve_hdus(hdul)
    assert described == [
        {
            "index": 1,
            "name": "RATE",
            "rate_columns": ["RATE"],
            "n_rows": 30,
            "n_bands": 3,
            "timeunit": "s",
            "has_mjdref": True,
            "telescope": "eROSITA",
            "instrument": None,
        }
    ]


def test_tables_without_time_or_rate_are_rejected(tmp_path):
    path = tmp_path / "bad.fits"
    fits.HDUList(
        [fits.PrimaryHDU(), fits.BinTableHDU.from_columns([fits.Column("X", "D", array=[1.0])])]
    ).writeto(path)
    with pytest.raises(LightcurveFileError, match="no light-curve table"):
        _read(path)


# --- service, storage and projects --------------------------------------


@pytest.fixture
def granted(monkeypatch):
    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)

    def grant(path):
        return str(path), make_grant(path, "read")

    return grant


def test_loaded_light_curve_is_stored_with_file_provenance(tmp_path, granted):
    state = StateManager()
    service = LightcurveService(state)
    path, token = granted(nicer_like(tmp_path / "nicer.lc"))
    result = service.load_lightcurve_file(path, token, output_name="nicer lc")
    assert result["success"], result
    json.dumps(result, allow_nan=False)
    data = result["data"]
    assert data["name"] == "nicer lc"
    assert data["operation"] == "lightcurve_from_fits"
    source = data["inputs"][0]
    assert source["kind"] == "fits_file"
    assert source["source_name"] == "nicer.lc"
    assert source["hdu"] == {"index": 1, "name": "RATE"}
    assert str(tmp_path) not in json.dumps(data)
    listed = service.list_lightcurves()["data"]
    assert [entry["name"] for entry in listed] == ["nicer lc"]


def test_loaded_light_curve_errors_are_reported(tmp_path, granted):
    service = LightcurveService(StateManager())
    path, token = granted(generic_counts(tmp_path / "plain.fits"))
    result = service.load_lightcurve_file(path, token, output_name="plain")
    assert result["success"] is False
    assert "MJDREF" in result["message"]


def test_power_spectrum_from_a_loaded_light_curve_names_its_lineage(tmp_path, granted):
    state = StateManager()
    path, token = granted(nicer_like(tmp_path / "nicer.lc"))
    assert LightcurveService(state).load_lightcurve_file(path, token, "lc")["success"]
    spectra = SpectrumService(state)
    single = spectra.create_power_spectrum(lightcurve_name="lc", dt=None, norm="leahy")
    assert single["success"], single
    source = single["data"]["inputs"][0]
    assert source["kind"] == "lightcurve"
    assert source["name"] == "lc"
    assert source["lineage"]["inputs"][0]["source_name"] == "nicer.lc"
    averaged = spectra.create_averaged_power_spectrum(
        lightcurve_name="lc", dt=None, segment_size=20.0, norm="leahy"
    )
    assert averaged["success"], averaged
    assert averaged["data"]["n_segments"] == 5  # 100 s of GTI in 20 s segments


def test_loaded_light_curves_round_trip_through_projects(tmp_path, granted):
    state = StateManager()
    path, token = granted(rxte_like(tmp_path / "pca.lc"))
    assert LightcurveService(state).load_lightcurve_file(path, token, "pca")["success"]
    project = tmp_path / "lc.srproj"
    saved = ProjectService(state_manager=state).save(
        str(project), make_grant(project, "write"), {}, None
    )
    assert saved["success"], saved
    restored = StateManager()
    opened = ProjectService(state_manager=restored).reopen(
        str(project), make_grant(project, "read")
    )
    assert opened["success"], opened
    original = state.get_lightcurve_data("pca")
    reopened = restored.get_lightcurve_data("pca")
    np.testing.assert_array_equal(reopened.counts, original.counts)
    assert reopened.result_identity == original.result_identity


def test_stream_reader_accepts_in_memory_files(tmp_path):
    raw = swift_like(tmp_path / "xrt.lc").read_bytes()
    lc, _, _ = read_lightcurve_fits(io.BytesIO(raw))
    assert len(lc.time) == 50


# --- routes --------------------------------------------------------------


@pytest.fixture
def app(monkeypatch):
    from main import create_app
    from tests.backend_auth import TEST_BACKEND_SESSION_SECRET

    monkeypatch.setenv("STINGRAY_FILE_GRANT_SECRET", TEST_SECRET)
    application = create_app(session_secret=TEST_BACKEND_SESSION_SECRET)
    application.state.state_manager = StateManager()
    application.state.performance_monitor = None
    return application


async def _post(app, path, body):
    import httpx

    from tests.backend_auth import TEST_BACKEND_AUTH_HEADERS

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=TEST_BACKEND_AUTH_HEADERS,
    ) as client:
        return await client.post(path, json=body)


@pytest.mark.asyncio
async def test_light_curve_file_routes_inspect_load_and_feed_spectra(app, tmp_path):
    path = multiband(tmp_path / "erosita.fits")
    grant = make_grant(path, "read")
    inspected = await _post(
        app, "/api/lightcurve/inspect-file", {"file_path": str(path), "file_grant": grant}
    )
    assert inspected.json()["data"]["tables"][0]["n_bands"] == 3

    loaded = await _post(
        app,
        "/api/lightcurve/from-file",
        {"file_path": str(path), "file_grant": grant, "output_name": "soft", "band": 0},
    )
    assert loaded.json()["success"], loaded.json()

    spectrum = await _post(
        app, "/api/spectrum/power-spectrum", {"lightcurve_name": "soft", "norm": "frac"}
    )
    assert spectrum.json()["success"], spectrum.json()
    assert spectrum.json()["data"]["inputs"][0]["lineage"]["inputs"][0]["band"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,message",
    [
        ({"dt": 1.0}, "exactly one"),
        ({"event_list_name": "a", "lightcurve_name": "b", "dt": 1.0}, "exactly one"),
        ({"event_list_name": "a"}, "dt is required"),
        (
            {"lightcurve_name": "b", "selection": {"energy_range": [1, 2]}},
            "Photon selections apply to event lists",
        ),
    ],
)
async def test_power_spectrum_sources_are_validated(app, body, message):
    response = await _post(app, "/api/spectrum/power-spectrum", body)
    assert response.status_code == 422
    assert message in response.text


@pytest.mark.asyncio
async def test_missing_light_curve_and_mismatched_dt_are_reported(app, tmp_path):
    path = swift_like(tmp_path / "xrt.lc")
    await _post(
        app,
        "/api/lightcurve/from-file",
        {"file_path": str(path), "file_grant": make_grant(path, "read"), "output_name": "xrt"},
    )
    missing = await _post(app, "/api/spectrum/power-spectrum", {"lightcurve_name": "nope"})
    assert "not found" in missing.json()["message"]
    mismatched = await _post(
        app, "/api/spectrum/power-spectrum", {"lightcurve_name": "xrt", "dt": 0.5}
    )
    assert "2.0 s bins" in mismatched.json()["message"]
