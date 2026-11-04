"""Run actual project fixtures in separately installed supported runtimes.

Usage: python tests/run_project_compatibility_matrix.py --runtime 2.2=/tmp/stingray220
       --runtime 2.2.10= --runtime 2.3.2=/tmp/stingray232 --directory /tmp/matrix
Install each external runtime with pip --no-deps --target first. The installed
application runtime is represented by an empty package directory after '='.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="append", required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=False)
    runtimes = [item.split("=", 1) for item in args.runtime]
    worker = Path(__file__).with_name("project_compatibility_worker.py")

    def run(mode, version, package, path):
        command = [sys.executable, str(worker), mode, str(path), "--expected", version]
        if package:
            command.extend(["--package-dir", package])
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(
                f"{mode} {version} {path.name}\n{result.stdout}\n{result.stderr}"
            )
        return result.stdout

    for version, package in runtimes:
        print(
            run("write", version, package, directory / f"{version}.srproj"), flush=True
        )
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [
            pool.submit(run, "read", version, package, directory / f"{source}.srproj")
            for source, _ in runtimes
            for version, package in runtimes
        ]
        for job in jobs:
            print(job.result(), flush=True)
    print(
        f"PASS: {len(runtimes)} real writers, {len(jobs)} real reopen/rebin/export-projection checks"
    )


if __name__ == "__main__":
    main()
