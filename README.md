# Stingray Explorer

Stingray Explorer is a desktop application for X-ray timing analysis. It combines
an Electron and React interface with a loopback FastAPI service backed by
[Stingray](https://docs.stingray.science/), Astropy, and NumPy.

> [!IMPORTANT]
> The original Panel, public Docker, and Hugging Face Spaces runtime has been
> retired. It accepted browser-controlled local paths, arbitrary download URLs,
> and unsafe serialization formats that do not belong at a public web boundary.
> The files still under `modules/`, root `services/`, and `utils/` are migration
> reference code; they are not a supported application entrypoint.

## Current application

The supported runtime is the Electron desktop app:

- React, TypeScript, Material UI, and Plotly provide the renderer.
- Electron owns native file dialogs and launches the Python service.
- FastAPI exposes the local scientific API on an ephemeral loopback port.
- Native selections are represented by short-lived grants instead of accepting
  paths typed by renderer code.
- Stingray performs event-list, light-curve, spectral, timing, correlation,
  variable-energy, and dead-time analyses.

The desktop UI includes data ingestion, HEASARC archive browsing, quick-look
analysis pages, job progress, logs, and utility workflows for General I/O, GTIs,
mission I/O, statistics, and miscellaneous Stingray helpers.

## Development setup

Install [Pixi](https://pixi.sh/) and a Node version supported by the locked
frontend toolchain, then run:

```bash
pixi install
npm install
npm run dev
```

Electron starts and authenticates the Python service automatically. Running the
FastAPI service as an unrelated external process is intentionally unsupported;
it cannot share Electron's per-launch credentials or native file grants.

Useful commands:

```bash
# Backend tests in the development environment
pixi run -e dev pytest python-backend/tests

# Frontend tests, type checking, linting, and production build
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

Additional scripts and packaging targets are listed in `package.json` and
`pixi.toml`.

## Repository layout

```text
electron/          Electron main process, preload bridge, and backend lifecycle
python-backend/    Authenticated FastAPI routes, services, models, and tests
src/               React renderer, API clients, state, pages, and component tests
files/             Small sample data used for development
resources/         Desktop application icons and packaging resources
docs/              Implementation plans and engineering notes
```

The historical Panel implementation remains in the legacy root Python folders
while migration work is completed. It has no executable `explorer.py`, Docker
image, or deployment workflow.

## Data and exports

Use the desktop application's native open and save dialogs for local files.
General I/O is the maintained export path; the duplicate raw-path `/api/export/*`
API has been retired. User-visible outputs are expected to use explicit formats,
refuse unintended overwrite, and pass format-specific verification before
publication.

Large scientific files are intentionally not tracked. The small examples under
`files/data/` are suitable for local development; use your own mission data for
full-scale analysis.

Named power spectra, averaged power spectra, cross spectra, and their rebinned
products are available in General I/O as **spectrum** objects. Complex spectra
export real and imaginary components alongside magnitude and phase; frequency
bin widths and averaging information are retained. ECSV, JSON, FITS, and
available HDF5 exports carry the result's identity and calculation record. CSV
preserves numeric columns and explicitly reports its metadata loss. Dynamical
two-dimensional spectra are listed with an explanation when tabular export is
unavailable.

Every newly calculated spectrum and light curve has a unique result ID, a
backend session ID, and a frozen record of its original inputs and requested
and effective settings. Rebinning creates a new result with parent lineage.
Stored output names cannot silently replace an existing product. General I/O
binds spectrum exports to the selected result ID, and rebin requests can bind
their source ID, so a reused name cannot silently change the selected result.

QuickLook retains original calculation inputs beside each result. Editing
controls or failing a later request does not relabel the previous plot. After
a backend restart, retained plots are marked read-only and backend actions
require a current product. Data Ingestion and Utilities reset their selections,
file grants, and workflow handoffs; late responses from an older backend are
discarded. Use saved analysis projects (described below) to persist and reopen a workspace across launches.

## Scientific analysis contracts

- Pair analyses require equal finite MJD references and compatible time-system,
  time-reference, and ephemeris metadata. Known metadata on only one input is
  rejected. Unknown metadata on both inputs remains usable, but does not
  establish an independently verified physical time reference. Align different
  origins or time scales explicitly before analysis.
- Paired Fourier analyses use a common event-binning origin and require a bin
  width compatible with both known instrument time resolutions. Returned
  effective settings describe the calculation, including segment rounding.
- Light-curve GTI selections intersect native exposure and retain only complete
  bins on the original light-curve grid. Gaps are excluded from the stored
  product and mean-rate calculation.
- Correlation requires one continuous native or common GTI. Exactly adjacent
  intervals are continuous; positive gaps are rejected. Use GTI Utilities to
  select a continuous interval before correlating a gapped observation.
- Power colours use noise-subtracted integrated fractional variances, with
  PC1 = C/A and PC2 = B/D following
  [Heil et al. (2015)](https://arxiv.org/abs/1405.2024). The calculation assumes
  ideal Poisson counting noise and does not model detector dead time or
  background. Ratios require positive variances detected at least three
  propagated standard errors above zero in all four bands; other segments keep
  their variance estimates and report null ratios. These are exploratory
  per-segment estimates, with approximate errors for sparsely sampled bands,
  and must not be interpreted directly as source states.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Stingray Explorer builds on the work of the Stingray, Astropy, HoloViz, and
broader X-ray astronomy communities.

## Saved analysis projects

In **Utilities → General I/O → Analysis projects**, save a `.srproj` file or
select one to reopen. Projects embed loaded EventLists, light curves, spectra,
stored analysis objects, and the latest successful QuickLook result per analysis
with its submitted settings and original provenance. Reopened QuickLook pages show the saved result and original-input record.
Selected inputs, unsent form edits (including incomplete values), tabs, plot
scales and numeric zoom ranges, theme, and layout preferences are saved too.
Use the header Save analysis project action to save directly from the current
page; reopening restores that page. Forms retain drafts when navigating away. Native file grants and credentials are excluded.

Reopening adds the fully validated project atomically and refuses conflicting
object names. Restart the backend to obtain an empty workspace before reopening
an existing session. Original scientific result and dataset IDs are preserved;
renderer lifecycle bindings are renewed for the current backend. Historical
results saved as stale remain read-only. Save uses verified exclusive publication
and never overwrites an existing file. New projects use a versioned ZIP64 archive with streamed, lossless NumPy arrays
and SHA-256 checksums. Scientific arrays are no longer limited to 128 MiB and
are not expanded into base64 JSON. Reopening verifies the archive before
allocating scientific arrays and checks available memory. JSON metadata has a
64 MiB limit; older v1 JSON projects remain readable with their original limit.
No pickle or executable deserialization is used. Project compatibility supports the released 2.2 series (2.2/2.2.0,
2.2.1–2.2.7, 2.2.9, 2.2.10) and 2.3.0–2.3.2. Unknown, prerelease,
development, and locally modified versions are rejected before decoding.
Cross-version reopening preserves stored scientific arrays, result identities,
and original software provenance. Missing runtime defaults are added without
recomputing or replacing saved values. A compatibility receipt reports the source
and current versions; migration history survives re-saving. New calculations
use the current Stingray runtime and may differ from historical calculations. Unsupported scientific object attributes
cause an explicit save failure rather than silent omission.


Project compatibility regression coverage includes a real-runtime subprocess
matrix in `python-backend/tests/run_project_compatibility_matrix.py`. Install
Stingray releases in separate directories with `pip install --no-deps --target`,
then pass `--runtime VERSION=DIRECTORY` for each installation (an empty directory
argument uses the application runtime) and a fresh `--directory` for fixtures.
The tested matrix uses 2.2, 2.2.10, and 2.3.2 as writers and readers in all nine
combinations, comparing saved arrays and complete identity records and exercising
subsequent light-curve/spectrum rebinning and scientific export projections.
Full application scientific-suite validation is recorded in
`docs/validation/scientific-compatibility-2026-10-30.json`: each of the 13 allowed
releases passed 1,386 backend tests with 14 Windows-only skips. This is a fixed-stack
macOS arm64 matrix (Python 3.14.2, NumPy 2.3.5, SciPy 1.16.3, Astropy 7.2.0),
not validation of all Python, dependency, and operating-system combinations.


### Repeating the scientific compatibility suite

`scripts/scientific_compatibility.py` runs the entire `python-backend/tests` suite
under separately installed Stingray packages. Install releases with
`python -m pip install --no-deps --target DIRECTORY stingray==VERSION`, using the
application's scientific Python environment. Pass one `--runtime VERSION=DIRECTORY`
argument per release; an empty directory uses the interpreter's installed release.
`--require-supported` verifies that all 13 allowlisted releases are included.
`--output DIRECTORY` receives per-version logs, JUnit XML, dependency/runtime
metadata, a source checksum, and `results.json`. The default `--jobs 2` bounds
concurrency. Each runtime has its own working directory because older Stingray
writers create fixed-name probe files.

Compatibility adapters apply to new calculations and exports. They enforce a
consistent instrument-clock binning policy, propagate standard light-curve
uncertainties on both sides of upstream's rebin-error fix, use the number of
averaged spectra in the raw-coherence bias term, and backport the low-count RMS
safety guard. Older FITS commentary is serialized without discarding repeated
cards, and unsupported FITS-reader keyword arguments are filtered while retained
RMF streams remain pinned. Runtime capability checks continue to report unavailable
mission conversions explicitly.

Stingray 2.3.0 has an upstream Numba import/compilation regression. The application
leaves that fallback mode intact, evaluates its documented coherence expression
directly, and selectively accelerates unchanged Zhang-model coefficient kernels
with Numba when available. Frequency-independent coefficients are calculated once;
the model order, physics, frequency grid, and interpolation are retained.
The implementation is checked against the public upstream dead-time model.
Existing saved result values, IDs and provenance are never recomputed by these
adapters. Nine reopening checks against previously created project archives
verified their arrays and complete identity records and confirmed that the
original archive bytes remained unchanged.

### Cross-platform verification

`.github/workflows/cross-platform.yml` runs the entire backend suite on
`ubuntu-24.04` for every one of the 13 supported Stingray releases. Windows
validation is deferred at the user's request: a manual dispatch with
`include_windows` enables the same jobs on `windows-2025`. It remains opt-in
because the exploratory Windows run exposed unresolved OGIP/FITS snapshot cleanup
failures (a third-party FITS mapping still holds the temporary file open).
Separate jobs run all renderer/Electron unit tests, type checking, ESLint and
the production build on the selected operating systems. The scientific stack
is fixed in `ci/scientific-constraints.txt`; test dependencies are in
`ci/test-requirements.txt`. Jobs require the actual target OS, HDF5 and PyTables,
and Windows jobs require the real NTFS grant/publication capability gate.
Results include JUnit XML, full backend logs, dependency versions and a checksum
of the tested backend source. Actions are pinned to verified commit hashes.

When Windows is enabled, the workflow also exchanges real project files between
independent Windows and Linux jobs. Linux-only runs check their local fixture. `scripts/project_platform_fixture.py` checks exact saved event,
light-curve and complex spectrum arrays, unsigned and endian-specific dtypes,
masks, workspace drafts, complete identities and provenance, and the unchanged
SHA256 of each original archive. It does not recompute the saved spectra.

To reproduce a complete backend run in an existing environment:

```sh
python -m pip install -r ci/test-requirements.txt -c ci/scientific-constraints.txt 'stingray==2.2.10'
python scripts/check_platform.py --expected Linux  # Use Windows on Windows.
python scripts/scientific_compatibility.py --runtime 2.2.10= --jobs 1 --output test-results/backend
npm ci
npx vitest run --maxWorkers=1
npm run typecheck
npm run lint
npm run build
```

Windows source installations need the Microsoft Visual C++ v14 runtime used by
scientific extension wheels; a missing runtime can prevent NumExpr/PyTables from
importing even when their Python packages are installed. Microsoft's supported
redistributable is documented at
<https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist>.

Manual GTI utility inputs use binary64 arithmetic consistently across platforms,
matching the JSON input/output precision. This prevents platform-dependent
`longdouble` widths from changing exposure splitting and overflow checks. Private
OGIP/FITS snapshots are always written in binary mode, including on Windows.
Development launches locate `python.exe` in the Windows Pixi environment root.

New project archives retain the original bytes and floating format of extended
real/complex arrays. They additionally store a portable projection only when
every real and imaginary component is exactly representable in binary64. The
projection is checked and written in bounded chunks. Readers with the same
floating format restore the original dtype; other readers use the exact
projection. Values requiring unavailable precision cause an explicit failure
before scientific-array allocation or state import. Saved provenance and source
archives are not rewritten. Legacy archives without floating-format metadata
retain their existing reader behavior; transferring legacy extended-precision
arrays to a different numeric ABI is not certified. Re-save those projects with
the current application on their original platform before transferring them.

The executed 2026-10-30 cross-platform pass is recorded in
`docs/validation/cross-platform-compatibility-2026-10-30.json`. On Linux arm64,
all 13 supported Stingray releases passed 1,398 backend tests each (18,174
passing test executions), with 14 NTFS-only and three Python-3.14-warning-mode
skips per release. The stack used Python 3.12.16, NumPy 2.3.5, SciPy 1.16.3 and
Astropy 7.2.0. Linux renderer testing passed 297 tests in 55 files, type checking,
ESLint (two existing warnings) and the production build. A macOS regression run
passed 1,397 backend tests with 18 expected skips. Nine historical project checks
and nine synthetic project writer/reader combinations preserved saved values,
identities, provenance and original archive hashes. Windows certification was
explicitly deferred; its exploratory run is not an all-platform pass. Hosted
Ubuntu x64/Windows CI and application installer/GUI testing have not been run.
