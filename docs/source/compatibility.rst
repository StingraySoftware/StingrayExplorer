Stingray compatibility
======================

Supported releases
------------------

The application is developed against Stingray 2.3.2 and supports 13 releases:
2.2 (also written 2.2.0), 2.2.1 to 2.2.7, 2.2.9, 2.2.10, and 2.3.0 to 2.3.2.
Any other version, including pre-releases and development builds, is refused
when a project is opened.

Compatibility adapters
----------------------

Small adapters keep new calculations and exports consistent across releases.
They:

* bin events on the instrument clock in the same way on every release;
* propagate standard light-curve errors on both sides of Stingray's rebin-error
  fix;
* use the number of averaged spectra in the raw-coherence bias term;
* back-port the low-count rms safety guard;
* filter by detector and time with explicit masks, because
  ``filter_detector_id`` only exists from 2.2.9 and ``filter_at_time_intervals``
  only from 2.2.4;
* fall back to 64-bit times where a release cannot handle extended precision
  (see :doc:`science`).

They also keep repeated FITS commentary cards when serialising, and drop FITS
reader options that an older release does not accept.

Stingray 2.3.0 has a Numba import regression. The application leaves that
fallback mode in place, evaluates the documented coherence expression directly,
and accelerates the unchanged Zhang dead-time coefficient kernels with Numba
when it is available.

Adapters never recompute saved results: saved values, IDs and records are kept
as they were.

When the installed release lacks a capability, for example a mission
conversion, the application reports it as unavailable rather than failing
silently.

Checking several releases
-------------------------

``scripts/scientific_compatibility.py`` runs the whole backend test suite under
separately installed Stingray releases. Install each release into its own
folder, with the application's Python:

.. code-block:: bash

   python -m pip install --no-deps --target /path/to/sr-2.2.10 stingray==2.2.10

then pass one ``--runtime VERSION=DIRECTORY`` per release. An empty directory
means the release installed in the interpreter:

.. code-block:: bash

   python scripts/scientific_compatibility.py \
     --runtime 2.2.10=/path/to/sr-2.2.10 --runtime 2.3.2= \
     --jobs 2 --output test-results/backend

``--require-supported`` checks that all 13 releases were included. The output
folder receives per-release logs, JUnit XML, runtime details, a checksum of the
tested source and ``results.json``. Each release gets its own working folder,
because older Stingray releases write probe files with fixed names.

``python-backend/tests/run_project_compatibility_matrix.py`` does the same for
projects: every chosen release writes a project and every one reopens it, and
the saved arrays and identity records are compared.

Continuous integration
----------------------

``.github/workflows/cross-platform.yml`` runs on every push to ``main`` and on
pull requests:

* the full backend suite on Ubuntu for each of the 13 releases;
* the renderer and Electron unit tests, type checking, ESLint and the
  production build;
* reopening project files written by the backend jobs;
* a repository check that no ``AI_DOCS/`` or ``.claude/`` path is tracked.

The scientific stack is pinned in ``ci/scientific-constraints.txt`` and the
test dependencies in ``ci/test-requirements.txt``.

Windows
-------

Windows jobs are opt-in: a manual run with ``include_windows`` adds them. They
are not yet part of the default run because a third-party FITS mapping keeps
temporary OGIP/FITS snapshots open, which makes their cleanup fail on NTFS.

Windows source installs need the Microsoft Visual C++ v14 runtime, which the
scientific extension wheels use; without it NumExpr and PyTables may fail to
import.

Validation records
------------------

Dated records of full validation runs are kept in ``docs/validation/``.
