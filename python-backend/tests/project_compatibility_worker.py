"""Subprocess fixture generator/consumer for real installed-version checks."""

import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["write", "read"])
    parser.add_argument("path")
    parser.add_argument("--package-dir")
    parser.add_argument("--expected", required=True)
    arguments = parser.parse_args()
    if arguments.package_dir:
        sys.path.insert(0, arguments.package_dir)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import os
    import json
    import numpy as np
    import stingray
    from stingray import EventList, DynamicalPowerspectrum
    from stingray.bispectrum import Bispectrum
    from services.project_service import ProjectService
    from services.state_manager import StateManager
    from services.spectrum_service import SpectrumService
    from services.lightcurve_service import LightcurveService
    from services.spectrum_products import spectrum_table
    from tests.test_io_utility_service import TEST_SECRET, make_grant

    assert stingray.__version__ == arguments.expected, stingray.__version__
    os.environ["STINGRAY_FILE_GRANT_SECRET"] = TEST_SECRET
    path = Path(arguments.path)
    state = StateManager()
    service = ProjectService(state_manager=state)
    if arguments.mode == "write":
        for name, offset in [("a", 0), ("b", 0.001)]:
            state.add_event_data(
                name,
                EventList(
                    time=np.arange(0.01, 32, 0.02) + offset,
                    gti=[[0, 32]],
                    mjdref=np.longdouble("55000.123456789012345"),
                ),
            )
        spectra = SpectrumService(state_manager=state)
        for result in [
            spectra.create_power_spectrum("a", 0.125, output_name="power"),
            spectra.create_cross_spectrum("a", "b", 0.125, output_name="cross"),
            spectra.create_averaged_power_spectrum(
                "a", 0.125, 8, output_name="averaged"
            ),
            spectra.create_averaged_cross_spectrum(
                "a", "b", 0.125, 8, output_name="averaged-cross"
            ),
        ]:
            assert result["success"], result
        result = LightcurveService(
            state_manager=state
        ).create_lightcurve_from_event_list("a", 0.125, "curve")
        assert result["success"], result
        state.add_analysis_result(
            "bispectrum", Bispectrum(state.get_lightcurve_data("curve"), maxlag=4)
        )
        state.add_analysis_result(
            "dynamic",
            DynamicalPowerspectrum(
                state.get_lightcurve_data("curve"), segment_size=8, sample_time=0.125
            ),
        )
        result = service.save(
            str(path),
            make_grant(path, "write"),
            {},
            {"version": 1, "fields": {"draft": "unfinished"}},
        )
        assert result["success"], result
        np.savez(
            str(path) + ".expected.npz",
            times=state.get_event_data("a").time,
            counts=state.get_lightcurve_data("curve").counts,
            bispectrum=state.get_analysis_result("bispectrum").bispec,
            dynamic=state.get_analysis_result("dynamic").dyn_ps,
            **{name: obj.power for name, obj in state.get_spectrum_data()},
        )
        Path(str(path) + ".identity.json").write_text(
            json.dumps(
                {name: obj.result_identity for name, obj in state.get_spectrum_data()}
            )
        )
    else:
        result = service.reopen(str(path), make_grant(path, "read"))
        assert result["success"], result
        expected = np.load(str(path) + ".expected.npz", allow_pickle=False)
        np.testing.assert_array_equal(state.get_event_data("a").time, expected["times"])
        assert state.get_event_data("a").mjdref == np.longdouble(
            "55000.123456789012345"
        )
        np.testing.assert_array_equal(
            state.get_lightcurve_data("curve").counts, expected["counts"]
        )
        np.testing.assert_array_equal(
            state.get_analysis_result("bispectrum").bispec, expected["bispectrum"]
        )
        np.testing.assert_array_equal(
            state.get_analysis_result("dynamic").dyn_ps, expected["dynamic"]
        )
        identities = json.loads(Path(str(path) + ".identity.json").read_text())
        for name, obj in state.get_spectrum_data():
            assert obj.result_identity == identities[name]
            np.testing.assert_array_equal(obj.power, expected[name])
            assert (
                obj.result_identity["provenance"]["stingray_version"]
                == result["data"]["compatibility"]["source_stingray_version"]
            )
            spectrum_table(obj)
            rebinned = SpectrumService(state_manager=state).rebin_spectrum(
                name,
                2,
                output_name=name + "-new",
                expected_result_id=obj.result_identity["result_id"],
            )
            assert rebinned["success"], rebinned
        rebinned = LightcurveService(state_manager=state).rebin_lightcurve(
            "curve", 2, "new-curve"
        )
        assert rebinned["success"], rebinned
        print(result["data"]["compatibility"])
    print("PASS", arguments.mode, stingray.__version__, path.name)


if __name__ == "__main__":
    main()
