"""Fail if git tracks local assistant settings or private reference material.

AI_DOCS/ and .claude/ stay on the maintainer's machine; .gitignore keeps them
out of normal commits, and this check catches a forced add at any depth or in
any letter case.
"""

import argparse
import subprocess
import sys

PRIVATE_PATHSPECS = (
    ":(icase,glob)**/AI_DOCS/**",
    ":(icase,glob)**/.claude/**",
)


def tracked_private_paths(repository):
    listing = subprocess.run(
        ["git", "-C", repository, "ls-files", "-z", "--", *PRIVATE_PATHSPECS],
        check=True,
        capture_output=True,
    )
    return [path for path in listing.stdout.decode("utf-8").split("\0") if path]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=".")
    args = parser.parse_args()
    offending = tracked_private_paths(args.repository)
    if offending:
        print(
            "These paths must not be tracked (remove them with git rm --cached):",
            *offending,
            sep="\n  ",
            file=sys.stderr,
        )
        return 1
    print("No AI_DOCS/ or .claude/ paths are tracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
