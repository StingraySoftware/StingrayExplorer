"""Run the full backend suite in isolated Stingray installations.

Example: python scripts/scientific_compatibility.py --runtime 2.2=/tmp/stingray220
         --runtime 2.2.10= --output /tmp/scientific-matrix --jobs 2
Dependencies other than Stingray come from this interpreter's environment.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WORKER = """
import sys,json,platform,os
from pathlib import Path
package, expected, output, root = sys.argv[1:]
if package:
    sys.path.insert(0, package)
    # Standalone fixture-tool subprocesses must use this same Stingray release.
    os.environ["PYTHONPATH"] = package + os.pathsep + str(Path(root)/"python-backend")
sys.path.insert(0, str(Path(root)/"python-backend"))
import stingray,numpy,scipy,astropy,pytest
from packaging.version import Version
assert Version(stingray.__version__) == Version(expected), (expected,stingray.__version__)
if package: assert Path(stingray.__file__).resolve().is_relative_to(Path(package).resolve())
print(json.dumps(dict(stingray=stingray.__version__,numba_enabled=stingray.utils.HAS_NUMBA, origin=stingray.__file__,python=platform.python_version(),platform=platform.platform(),numpy=numpy.__version__,scipy=scipy.__version__,astropy=astropy.__version__)),flush=True)
sys.exit(pytest.main([str(Path(root)/'python-backend/tests'),'-c',str(Path(root)/'pyproject.toml'),'-q','-rs','--junitxml='+output]))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--require-supported", action="store_true")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    runtimes = [value.split("=", 1) for value in args.runtime]
    if args.require_supported:
        sys.path.insert(0, str(ROOT / "python-backend"))
        from services.project_compatibility import SUPPORTED
        from packaging.version import Version

        if {Version(version) for version, _ in runtimes} != SUPPORTED or len(
            runtimes
        ) != len(SUPPORTED):
            parser.error(
                "--require-supported needs exactly one installation per supported release"
            )

    digest = hashlib.sha256()
    sources = [
        ROOT / "python-backend/main.py",
    ]
    for folder in ("services", "routes", "tests"):
        sources.extend(sorted((ROOT / "python-backend" / folder).glob("*.py")))
    for source in sources:
        digest.update(source.relative_to(ROOT).as_posix().encode())
        digest.update(source.read_bytes())
    source_digest = digest.hexdigest()

    def run(item):
        version, package = item
        xml = output / f"{version}.xml"
        log = output / f"{version}.log"
        work = output / (version + "-work")
        work.mkdir(exist_ok=True)
        xml.unlink(missing_ok=True)
        with log.open("w", encoding="utf-8") as stream:
            process = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "-c",
                    WORKER,
                    package,
                    version,
                    str(xml),
                    str(ROOT),
                ],
                cwd=work,
                stdout=stream,
                stderr=subprocess.STDOUT,
            )
        row = dict(
            version=version,
            exit_code=process.returncode,
            log=str(log),
            source_sha256=source_digest,
        )
        if xml.exists():
            suites = ET.parse(xml).getroot()
            row.update(
                {
                    key: sum(int(suite.get(key, 0)) for suite in suites)
                    for key in ("tests", "errors", "failures", "skipped")
                }
            )
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.startswith('{"stingray":'):
                row["environment"] = json.loads(line)
                break
        if "tests" in row:
            row["passed"] = (
                row["tests"] - row["errors"] - row["failures"] - row["skipped"]
            )
        print(json.dumps(row), flush=True)
        return row

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        rows = list(pool.map(run, runtimes))
    (output / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return int(any(row["exit_code"] for row in rows))


if __name__ == "__main__":
    sys.exit(main())
