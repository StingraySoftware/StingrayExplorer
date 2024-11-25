---
title: Stingray Explorer
emoji: 🚀
colorFrom: gray
colorTo: green
sdk: docker
pinned: false
license: mit
thumbnail: >-
  https://cdn-uploads.huggingface.co/production/uploads/668d17c6e6887d1f6afde2a6/4q5lnlS6-eJ_JBh8tW3_I.png
short_description: Stingray Explorer Dashboard Demo
---
# StingrayExplorer

StingrayExplorer is a data analysis tool designed for quick visualization and exploration of astronomical time series data. It leverages the Stingray library to compute power spectra, cross spectra, and more, with a user-friendly dashboard built using Panel.

## Project Structure

```
.
├── CODE_OF_CONDUCT.md
├── Dockerfile
├── LICENSE
├── README.md
├── assets
│   ├── audio
│   ├── icons
│   │   ├── __pycache__
│   │   │   └── svg.cpython-311.pyc
│   │   └── svg.py
│   ├── images
│   │   ├── holoviz_logo.png
│   │   ├── holoviz_logo_minimised.png
│   │   ├── stingray_explorer.png
│   │   ├── stingray_explorer.webp
│   │   ├── stingray_explorer_minimised.png
│   │   ├── stingray_logo.png
│   │   └── stingray_logo_minimised.png
│   ├── stylesheets
│   │   └── explorer.css
│   └── videos
├── docs
│   ├── Makefile
│   ├── build
│   │   ├── doctrees
│   │   │   ├── DataLoading.doctree
│   │   │   ├── Home.doctree
│   │   │   ├── QuickLook.doctree
│   │   │   ├── environment.pickle
│   │   │   ├── index.doctree
│   │   │   └── modules.doctree
│   │   └── html
│   │       ├── DataLoading.html
│   │       ├── Home.html
│   │       ├── QuickLook.html
│   │       ├── _modules
│   │       │   ├── index.html
│   │       │   └── modules
│   │       │       ├── DataLoading
│   │       │       │   └── DataIngestion.html
│   │       │       ├── Home
│   │       │       │   └── HomeContent.html
│   │       │       └── QuickLook
│   │       │           ├── AverageCrossSpectrum.html
│   │       │           ├── AveragePowerSpectrum.html
│   │       │           ├── Bispectrum.html
│   │       │           ├── CrossSpectrum.html
│   │       │           ├── LightCurve.html
│   │       │           ├── PowerColors.html
│   │       │           └── PowerSpectrum.html
│   │       ├── _sources
│   │       │   ├── DataLoading.rst.txt
│   │       │   ├── Home.rst.txt
│   │       │   ├── QuickLook.rst.txt
│   │       │   ├── index.rst.txt
│   │       │   └── modules.rst.txt
│   │       ├── _static
│   │       │   ├── _sphinx_javascript_frameworks_compat.js
│   │       │   ├── basic.css
│   │       │   ├── css
│   │       │   │   ├── badge_only.css
│   │       │   │   ├── fonts
│   │       │   │   │   ├── Roboto-Slab-Bold.woff
│   │       │   │   │   ├── Roboto-Slab-Bold.woff2
│   │       │   │   │   ├── Roboto-Slab-Regular.woff
│   │       │   │   │   ├── Roboto-Slab-Regular.woff2
│   │       │   │   │   ├── fontawesome-webfont.eot
│   │       │   │   │   ├── fontawesome-webfont.svg
│   │       │   │   │   ├── fontawesome-webfont.ttf
│   │       │   │   │   ├── fontawesome-webfont.woff
│   │       │   │   │   ├── fontawesome-webfont.woff2
│   │       │   │   │   ├── lato-bold-italic.woff
│   │       │   │   │   ├── lato-bold-italic.woff2
│   │       │   │   │   ├── lato-bold.woff
│   │       │   │   │   ├── lato-bold.woff2
│   │       │   │   │   ├── lato-normal-italic.woff
│   │       │   │   │   ├── lato-normal-italic.woff2
│   │       │   │   │   ├── lato-normal.woff
│   │       │   │   │   └── lato-normal.woff2
│   │       │   │   └── theme.css
│   │       │   ├── doctools.js
│   │       │   ├── documentation_options.js
│   │       │   ├── file.png
│   │       │   ├── fonts
│   │       │   │   ├── Lato
│   │       │   │   │   ├── lato-bold.eot
│   │       │   │   │   ├── lato-bold.ttf
│   │       │   │   │   ├── lato-bold.woff
│   │       │   │   │   ├── lato-bold.woff2
│   │       │   │   │   ├── lato-bolditalic.eot
│   │       │   │   │   ├── lato-bolditalic.ttf
│   │       │   │   │   ├── lato-bolditalic.woff
│   │       │   │   │   ├── lato-bolditalic.woff2
│   │       │   │   │   ├── lato-italic.eot
│   │       │   │   │   ├── lato-italic.ttf
│   │       │   │   │   ├── lato-italic.woff
│   │       │   │   │   ├── lato-italic.woff2
│   │       │   │   │   ├── lato-regular.eot
│   │       │   │   │   ├── lato-regular.ttf
│   │       │   │   │   ├── lato-regular.woff
│   │       │   │   │   └── lato-regular.woff2
│   │       │   │   └── RobotoSlab
│   │       │   │       ├── roboto-slab-v7-bold.eot
│   │       │   │       ├── roboto-slab-v7-bold.ttf
│   │       │   │       ├── roboto-slab-v7-bold.woff
│   │       │   │       ├── roboto-slab-v7-bold.woff2
│   │       │   │       ├── roboto-slab-v7-regular.eot
│   │       │   │       ├── roboto-slab-v7-regular.ttf
│   │       │   │       ├── roboto-slab-v7-regular.woff
│   │       │   │       └── roboto-slab-v7-regular.woff2
│   │       │   ├── jquery.js
│   │       │   ├── js
│   │       │   │   ├── badge_only.js
│   │       │   │   ├── theme.js
│   │       │   │   └── versions.js
│   │       │   ├── language_data.js
│   │       │   ├── minus.png
│   │       │   ├── plus.png
│   │       │   ├── pygments.css
│   │       │   ├── searchtools.js
│   │       │   └── sphinx_highlight.js
│   │       ├── genindex.html
│   │       ├── index.html
│   │       ├── modules.html
│   │       ├── objects.inv
│   │       ├── py-modindex.html
│   │       ├── search.html
│   │       └── searchindex.js
│   ├── files
│   │   └── loaded-data
│   ├── make.bat
│   ├── requirements.txt
│   └── source
│       ├── DataLoading.rst
│       ├── Home.rst
│       ├── QuickLook.rst
│       ├── _static
│       ├── _templates
│       ├── conf.py
│       ├── index.rst
│       └── modules.rst
├── environment.yml
├── explorer.py
├── files
│   ├── data
│   │   ├── LightCurve_bexvar.fits
│   │   ├── data_small.hdf5
│   │   ├── data_smaller.hdf5
│   │   ├── lcurveA.fits
│   │   ├── lcurve_new.fits
│   │   ├── monol_testA.evt
│   │   ├── monol_testA_calib.evt
│   │   ├── monol_testA_calib_unsrt.evt
│   │   ├── nomission.evt
│   │   ├── xte_gx_test.evt.gz
│   │   └── xte_test.evt.gz
│   └── loaded-data
├── modules
│   ├── DataLoading
│   │   ├── DataIngestion.py
│   │   ├── __init__.py
│   │   └── __pycache__
│   │       ├── DataIngestion.cpython-311.pyc
│   │       └── __init__.cpython-311.pyc
│   ├── Home
│   │   ├── HomeContent.py
│   │   ├── __init__.py
│   │   └── __pycache__
│   │       ├── Home.cpython-311.pyc
│   │       ├── HomeContent.cpython-311.pyc
│   │       └── __init__.cpython-311.pyc
│   └── QuickLook
│       ├── AverageCrossSpectrum.py
│       ├── AveragePowerSpectrum.py
│       ├── Bispectrum.py
│       ├── CrossSpectrum.py
│       ├── LightCurve.py
│       ├── PowerColors.py
│       ├── PowerSpectrum.py
│       ├── __init__.py
│       └── __pycache__
│           ├── AverageCrossSpectrum.cpython-311.pyc
│           ├── AveragePowerSpectrum.cpython-311.pyc
│           ├── Bispectrum.cpython-311.pyc
│           ├── CrossSpectrum.cpython-311.pyc
│           ├── LightCurve.cpython-311.pyc
│           ├── PowerColors.cpython-311.pyc
│           ├── PowerSpectrum.cpython-311.pyc
│           └── __init__.cpython-311.pyc
├── pyproject.toml
├── setup.py
├── tests
│   ├── test_dataloading
│   │   ├── __pycache__
│   │   │   └── test_dataingestion.cpython-311-pytest-8.2.1.pyc
│   │   └── test_dataingestion.py
│   ├── test_quicklook
│   └── test_utils
└── utils
    ├── DashboardClasses.py
    ├── __pycache__
    │   ├── dashboardClasses.cpython-311.pyc
    │   ├── globals.cpython-311.pyc
    │   ├── sidebar.cpython-311.pyc
    │   └── strings.cpython-311.pyc
    ├── globals.py
    ├── sidebar.py
    └── strings.py

47 directories, 162 files
```

## Installation

### Prerequisites

- Python 3.11 or above
- Panel
- Holoviews
- Stingray
- Other dependencies listed in `environment.yml`

### Setup

1. Clone the repository:

    ```
    git clone https://github.com/kartikmandar-GSOC24/StingrayExplorer.git
    ```

2. Navigate to the project directory:

    ```
    cd StingrayExplorer
    ```

3. Create and activate the conda environment:

    ```bash
    conda env create -f environment.yml
    conda activate stingray-env
    ```
Note: In case of dependencies clashing refer to individual dependencies and see if the version is correct for Stingray installation. \
The most important dependencies are as follows:\
stingray, holoviews, panel\
You would need to install the various dependencies to install all this. 

If the import errors are still persisting, see what libraries absence is causing the import and install them from pip or conda forge. 

If nothing else works, contact me at kartik4321mandar@gmail.com or in the Stingray slack channel @kartikmandar

## Deployment

The dashboard can now be deployed using Docker and is live on Hugging Face Spaces at [https://kartikmandar-stingrayexplorer.hf.space/explorer](https://kartikmandar-stingrayexplorer.hf.space/explorer).

The Hugging Face Spaces repository is located at: [https://huggingface.co/spaces/kartikmandar/StingrayExplorer](https://huggingface.co/spaces/kartikmandar/StingrayExplorer).

A live demo of the application is also embedded on my website for easy access: [https://www.kartikmandar.com/gsoc-2024/stingray-explorer](https://www.kartikmandar.com/gsoc-2024/stingray-explorer).

### How to Deploy and Build Using Docker

To deploy the dashboard using Docker, follow these steps:

### Build the Docker Image:  
Navigate to the project directory and build the Docker image using the following command:

```bash
docker build -t stingray-explorer .
```

### Run the Docker Container

After building the image, run the container with the following command:

```bash
docker run -p 7860:7860 stingray-explorer
```




## GitHub Actions Integration

The Hugging Face Spaces repository is synced with the main GitHub repository using GitHub Actions. This sync occurs automatically for every commit pushed to the `main` branch.


## Usage

To run the StingrayExplorer application, execute inside StingrayExplorer:

```
panel serve explorer.py --autoreload --static-dirs assets=./assets
```

This will start a Panel server and launch the application in your default web browser.

## Modules

### `explorer.py`

The main entry point of the application. It initializes the Panel server and sets up the layout of the dashboard.

### `assets/`

Contains static assets like icons, images, stylesheets, audio, and video files used in the dashboard.

### `files/`

Contains example data files and event lists that can be loaded into the application for analysis.

### `modules/`

#### `DataLoading/`

- **DataIngestion.py**: Handles the loading and preprocessing of event list data.

#### `Home/`

- **HomeContent.py**: Contains the components and layout for the home screen of the dashboard.

#### `QuickLook/`

- **AverageCrossSpectrum.py**: Module for computing and visualizing averaged cross spectra.
- **AveragePowerSpectrum.py**: Module for computing and visualizing averaged power spectra.
- **CrossSpectrum.py**: Module for computing and visualizing cross spectra.
- **LightCurve.py**: Module for generating and displaying light curves.
- **PowerSpectrum.py**: Module for generating and displaying power spectra.

### `utils/`

- **DashboardClasses.py**: Contains reusable classes for constructing the dashboard layout and components.
- **globals.py**: Stores global variables and state used across different modules.
- **sidebar.py**: Manages the sidebar navigation and interactions.
- **strings.py**: Contains strings and messages used in the application.

## Features

- **Quick Visualization**: Easily generate and visualize light curves, power spectra, and cross spectra.
- **Data Loading**: Load and analyze different event list data sets.
- **Interactive UI**: Use a user-friendly interface to interact with the data and view results in real-time.
- **Floating Panels**: Separate panels for different plots and data frames, allowing for a customizable layout.

## Contributing

If you would like to contribute to this project, please follow the steps below:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The Stingray library for providing tools for X-ray astronomy data analysis.
- Panel and Holoviews (HoloViz ecosystem) for enabling interactive data visualization in Python.
