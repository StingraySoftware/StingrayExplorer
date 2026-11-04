"""Fail closed if a full-suite job is on the wrong OS or lacks scientific I/O."""

import argparse
import json
import platform


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected", choices=["Linux", "Windows", "macOS"], required=True
    )
    args = parser.parse_args()
    actual = platform.system()
    expected = "Darwin" if args.expected == "macOS" else args.expected
    if actual != expected:
        parser.error(f"Expected a native {expected} runtime; found {actual}")
    import h5py
    import tables
    import stingray
    import numpy as np

    print(
        json.dumps(
            dict(
                system=actual,
                machine=platform.machine(),
                python=platform.python_version(),
                stingray=stingray.__version__,
                h5py=h5py.__version__,
                tables=tables.__version__,
                longdouble_bits=np.finfo(np.longdouble).nmant + 1,
            )
        )
    )


if __name__ == "__main__":
    main()
