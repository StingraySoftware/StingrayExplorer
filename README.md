# Stingray Explorer

Stingray Explorer is a desktop application for X-ray spectral-timing analysis.
It puts a graphical interface on [Stingray](https://docs.stingray.science/):
load event lists or light curves, choose photons by energy, detector and time,
and compute power spectra, cross spectra, lags, coherence, dead-time
corrections, power colours and variability-versus-energy spectra. Every result
carries a full record of how it was made, and can be saved to a project file,
reopened later and exported.

The application combines an Electron shell, a React renderer and a FastAPI
service on a private loopback port that runs Stingray.

**Documentation:** <https://stingrayexplorer.readthedocs.io/>, built from
[`docs/source`](docs/source).

## Getting started

You need [Pixi](https://pixi.sh/) and [Git LFS](https://git-lfs.com/).

```bash
git lfs install
git clone https://github.com/StingraySoftware/StingrayExplorer.git
cd StingrayExplorer
pixi install
npm install
npx install-electron
npm run dev
```

Electron starts and authenticates the Python service itself. Running the
service as a separate process is not supported. Small sample files are in
`files/data/`; see `files/data/DATA_README.txt`.

## Development checks

```bash
pixi run -e dev pytest python-backend/tests -q
npx vitest run
npm run typecheck
npm run lint
pixi run -e dev ruff check python-backend scripts
npm run build
```

The [development guide](docs/source/development.rst) describes the layout, the
pattern every analysis follows, and the repository rules. The
[compatibility guide](docs/source/compatibility.rst) explains how to run the
backend suite under each of the 13 supported Stingray releases (2.2 to 2.3.2)
and what continuous integration runs.

## Repository layout

```text
electron/          Electron main process, preload bridge, and backend lifecycle
python-backend/    Authenticated FastAPI routes, services, models, and tests
src/               React renderer, API clients, state, pages, and component tests
scripts/           Compatibility, platform, and repository checks
files/             Small sample data used for development
resources/         Desktop application icons and packaging resources
docs/              Documentation, implementation plans, and validation records
```

## History

Stingray Explorer began as a Panel web application. That runtime, including
its public Docker image and Hugging Face Space, was retired because it accepted
browser-controlled local paths, arbitrary download URLs and unsafe
serialisation formats. Its source is preserved at the `panel-final` tag.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Stingray Explorer builds on the work of the Stingray, Astropy, HoloViz and
wider X-ray astronomy communities.
