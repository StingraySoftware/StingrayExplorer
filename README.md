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
├── assets
│   ├── audio
│   ├── icons
│   │   └── svg.py
│   ├── images
│   ├── stylesheets
│   │   └── explorer.css
│   └── videos
├── explorer.py
├── files
│   ├── data
│   └── loaded-data
├── modules
│   ├── DataLoading
│   │   ├── DataIngestion.py
│   ├── Home
│   │   ├── HomeContent.py
│   └── QuickLook
│       ├── AverageCrossSpectrum.py
│       ├── AveragePowerSpectrum.py
│       ├── CrossSpectrum.py
│       ├── LightCurve.py
│       ├── PowerSpectrum.py
├── utils
    ├── DashboardClasses.py
    ├── globals.py
    ├── sidebar.py
    └── strings.py
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
