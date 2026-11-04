"""Write/read real project interchange fixtures without recomputing saved results.

Used in CI to exchange artifacts between independent Linux and Windows jobs.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python-backend"))


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["write", "read"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    import numpy as np
    from stingray import EventList
    from services.project_service import ProjectService
    from services.state_manager import StateManager
    from services.spectrum_service import SpectrumService
    from services.lightcurve_service import LightcurveService
    from services.utility_helpers import issue_file_grant
    import os

    # Synthetic test-only secret, never part of the project or its evidence.
    os.environ["STINGRAY_FILE_GRANT_SECRET"] = (
        "platform-fixture-test-secret-at-least-32-bytes"
    )
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)

    def grant(path, access):
        return issue_file_grant(str(path), access=access).grant

    if args.mode == "write":
        state = StateManager()
        for name, offset in [("a", 0.0), ("b", 0.001)]:
            state.add_event_data(
                name,
                EventList(
                    time=np.arange(0.01, 32, 0.02, dtype=np.float64) + offset,
                    gti=np.array([[0, 32]], dtype=np.float64),
                    mjdref=np.float64(55000.125),
                ),
            )
        for result in [
            SpectrumService(state_manager=state).create_power_spectrum(
                "a", 0.125, output_name="power"
            ),
            SpectrumService(state_manager=state).create_averaged_cross_spectrum(
                "a", "b", 0.125, 8, output_name="cross"
            ),
            LightcurveService(state_manager=state).create_lightcurve_from_event_list(
                "a", 0.125, "curve"
            ),
        ]:
            assert result["success"], result
        state.add_analysis_result(
            "typed",
            {
                "unsigned": np.array([2**63 + 1, 2**64 - 1], dtype=np.uint64),
                "big_endian": np.array([1.25, -2.5], dtype=">f8"),
                "masked": np.ma.array([1.0, 2.0], mask=[False, True], fill_value=-99),
                "provenance": {"original_input": state.get_event_identity("a")},
            },
        )
        path = directory / f"{platform.system()}.srproj"
        renderer = {
            "Power": {"result": {"power": [1, 2]}, "resultInputs": {"name": "a"}}
        }
        workspace = {"version": 1, "fields": {"draft": "unfinished.", "selection": "a"}}
        saved = ProjectService(state_manager=state).save(
            str(path), grant(path, "write"), renderer, workspace
        )
        assert saved["success"], saved
        expected = dict(
            times=state.get_event_data("a").time,
            counts=state.get_lightcurve_data("curve").counts,
        )
        expected.update({name: obj.power for name, obj in state.get_spectrum_data()})
        np.savez(str(path) + ".npz", **expected)
        identity = dict(
            sha256=checksum(path),
            event={
                name: state.get_event_identity(name)
                for name in state.list_event_names()
            },
            curve=state.get_lightcurve_identity("curve"),
            spectra={
                name: obj.result_identity for name, obj in state.get_spectrum_data()
            },
            renderer=renderer,
            workspace=workspace,
        )
        Path(str(path) + ".json").write_text(json.dumps(identity), encoding="utf-8")
        print("PASS wrote", path.name, identity["sha256"])
        return
    paths = sorted(directory.rglob("*.srproj"))
    assert paths, "No project fixtures found"
    for path in paths:
        expected = json.loads(Path(str(path) + ".json").read_text(encoding="utf-8"))
        assert checksum(path) == expected["sha256"]
        state = StateManager()
        opened = ProjectService(state_manager=state).reopen(
            str(path), grant(path, "read")
        )
        assert opened["success"], opened
        with np.load(str(path) + ".npz", allow_pickle=False) as arrays:
            np.testing.assert_array_equal(
                state.get_event_data("a").time, arrays["times"]
            )
            np.testing.assert_array_equal(
                state.get_lightcurve_data("curve").counts, arrays["counts"]
            )
            for name, obj in state.get_spectrum_data():
                np.testing.assert_array_equal(obj.power, arrays[name])
                assert obj.result_identity == expected["spectra"][name]
        for name, identity in expected["event"].items():
            assert state.get_event_identity(name) == identity
        assert state.get_lightcurve_identity("curve") == expected["curve"]
        assert opened["data"]["renderer"] == expected["renderer"]
        assert opened["data"]["workspace"] == expected["workspace"]
        typed = state.get_analysis_result("typed")
        assert typed["unsigned"].dtype == np.dtype("uint64")
        np.testing.assert_array_equal(
            typed["unsigned"], np.array([2**63 + 1, 2**64 - 1], dtype=np.uint64)
        )
        assert typed["big_endian"].dtype.str == ">f8"
        np.testing.assert_array_equal(typed["big_endian"], [1.25, -2.5])
        np.testing.assert_array_equal(typed["masked"].mask, [False, True])
        assert typed["masked"].fill_value == -99
        assert typed["provenance"]["original_input"] == expected["event"]["a"]
        assert checksum(path) == expected["sha256"], (
            "Reopening changed the source archive"
        )
        print(
            "PASS reopened unchanged",
            path.name,
            "on",
            platform.system(),
            expected["sha256"],
        )


if __name__ == "__main__":
    main()
