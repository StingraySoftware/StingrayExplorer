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

StingrayExplorer is a comprehensive data analysis and visualization dashboard designed for X-ray astronomy time series data. Built on top of the Stingray library, it provides an intuitive graphical interface for analyzing event lists, generating light curves, computing various types of spectra, and performing advanced timing analysis.

## Overview

StingrayExplorer combines the powerful timing analysis capabilities of the Stingray library with a modern, interactive dashboard built using Panel and HoloViz. It enables astronomers to:

- Load and analyze event lists from various X-ray telescopes
- Generate and manipulate light curves
- Compute power spectra, cross spectra, and bispectra
- Analyze dynamical power spectra and power colors
- Visualize results through interactive plots
- Export analysis results in multiple formats

The dashboard is designed to be user-friendly while providing access to advanced features for experienced users.

## Key Features

### Data Loading and Management
- Support for multiple file formats (FITS, HDF5, ASCII, etc.)
- Batch loading of multiple event lists
- Automatic GTI (Good Time Interval) handling
- Energy calibration using RMF (Response Matrix File)
- File preview and metadata inspection

### Event List Analysis
- Event list creation and simulation
- Deadtime correction
- Energy filtering and PI channel conversion
- Event list joining and sorting
- Color and intensity evolution analysis

### Spectral Analysis
- Power spectrum computation
- Cross spectrum analysis
- Averaged power/cross spectra
- Bispectrum calculation
- Dynamical power spectrum visualization
- Power color analysis

### Interactive Visualization
- Real-time plot updates
- Customizable plot layouts
- Floating plot panels
- Interactive plot manipulation
- Multiple visualization options

### System Features
- Resource monitoring (CPU, RAM usage)
- Warning and error handling
- Comprehensive help documentation
- Responsive layout design

## Architecture

The project follows a modular architecture with clear separation of concerns:

### Core Components

1. **explorer.py**: Main entry point and dashboard initialization
   - Panel/HoloViz setup
   - Layout configuration
   - Component integration

2. **modules/**: Core functionality modules
   - **DataLoading/**: Data ingestion and management
   - **Home/**: Dashboard home page and navigation
   - **QuickLook/**: Analysis tools and visualizations
     - EventList handling
     - Light curve generation
     - Spectral analysis
     - Power color computation

3. **utils/**: Utility classes and functions
   - **DashboardClasses.py**: Reusable UI components
   - **sidebar.py**: Navigation and control
   - **globals.py**: Global state management
   - **strings.py**: Text content

4. **assets/**: Static resources
   - Images and icons
   - CSS stylesheets
   - Documentation assets

5. **files/**: Data storage
   - Sample data files
   - User-loaded data
   - Analysis outputs

### Technology Stack

- **Backend**: Python 3.11+
- **Frontend**: Panel, HoloViz
- **Data Analysis**: Stingray, NumPy, Astropy
- **Visualization**: Bokeh, Matplotlib
- **Deployment**: Docker, Hugging Face Spaces

## Installation Guide

### Prerequisites

- Python 3.11 or above
- Conda package manager
- Git (for cloning the repository)

### Dependencies

Core packages:
- Panel >= 1.3.0
- HoloViews >= 1.18.0
- Stingray >= 0.3
- NumPy >= 1.24.0
- Astropy >= 5.0
- Matplotlib >= 3.7.0
- Bokeh >= 3.3.0

### Setup Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/kartikmandar-GSOC24/StingrayExplorer.git
   cd StingrayExplorer
   ```

2. Create and activate the conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate stingray-env
   ```

3. Verify installation:
   ```bash
   python -c "import stingray; import panel; import holoviews"
   ```

### Troubleshooting Dependencies

If you encounter dependency conflicts:

1. Check individual package versions:
   ```bash
   conda list stingray
   conda list panel
   conda list holoviews
   ```

2. Try installing missing dependencies:
   ```bash
   conda install -c conda-forge <package_name>
   # or
   pip install <package_name>
   ```

3. Common issues:
   - Stingray version compatibility
   - Panel/HoloViews version mismatch
   - Missing system libraries

4. Support channels:
   - Email: kartik4321mandar@gmail.com
   - Stingray Slack: @kartikmandar
   - GitHub Issues

## Deployment Options

### Local Development Server

Run the application locally:
```bash
panel serve explorer.py --autoreload --static-dirs assets=./assets
```

This starts a development server with:
- Auto-reloading on file changes
- Static file serving
- Debug information
- Default port 5006

### Docker Deployment

1. Build the image:
   ```bash
   docker build -t stingray-explorer .
   ```

2. Run the container:
   ```bash
   docker run -p 7860:7860 stingray-explorer
   ```

3. Access the application at `http://localhost:7860`

### Hugging Face Spaces

The dashboard is deployed on Hugging Face Spaces:
- Live demo: [https://kartikmandar-stingrayexplorer.hf.space/explorer](https://kartikmandar-stingrayexplorer.hf.space/explorer)
- Repository: [https://huggingface.co/spaces/kartikmandar/StingrayExplorer](https://huggingface.co/spaces/kartikmandar/StingrayExplorer)
- Website demo: [https://www.kartikmandar.com/gsoc-2024/stingray-explorer](https://www.kartikmandar.com/gsoc-2024/stingray-explorer)

### Continuous Integration

GitHub Actions automatically sync changes to Hugging Face Spaces:
- Triggers on pushes to `main` branch
- Builds and deploys Docker image
- Updates Hugging Face Space

## Usage Guide

### Quick Start

1. Launch the application:
   ```bash
   panel serve explorer.py --autoreload --static-dirs assets=./assets
   ```

2. Navigate to `http://localhost:5006` in your browser

3. Basic workflow:
   - Use the sidebar navigation
   - Load data files
   - Generate visualizations
   - Export results

### Data Loading

1. Click "Read Data" in the sidebar
2. Choose from multiple options:
   - Load local files
   - Fetch from URL
   - Use sample data

Supported formats:
- FITS event files
- HDF5 files
- ASCII tables
- ECSV files

### Analysis Tools

1. **Event List Operations**
   - Create/simulate event lists
   - Apply deadtime corrections
   - Filter by energy range
   - Convert PI to energy

2. **Light Curve Analysis**
   - Generate light curves
   - Apply GTI filters
   - Compute statistics
   - Plot time series

3. **Spectral Analysis**
   - Compute power spectra
   - Generate cross spectra
   - Calculate bispectra
   - Analyze power colors

4. **Advanced Features**
   - Dynamical power spectra
   - Color evolution
   - Intensity analysis
   - Custom plotting

### Visualization Options

1. **Plot Types**
   - Time series
   - Spectral plots
   - Contour plots
   - Scatter plots

2. **Interactive Features**
   - Zoom/pan
   - Hover tooltips
   - Plot customization
   - Export options

3. **Layout Options**
   - Floating panels
   - Grid arrangements
   - Multiple views
   - Responsive design

### Data Export

- Save plots as PNG/SVG
- Export data as CSV/FITS
- Save analysis results
- Generate reports

## Development Guide

### Setting Up Development Environment

1. Fork and clone the repository
2. Create development environment:
   ```bash
   conda env create -f environment.yml
   conda activate stingray-env
   ```
3. Install development dependencies:
   ```bash
   pip install -r docs/requirements.txt
   ```

### Project Structure

```
stingray-explorer/
├── explorer.py          # Main application entry point
├── modules/            # Core functionality modules
│   ├── DataLoading/   # Data ingestion components
│   ├── Home/          # Dashboard home components
│   └── QuickLook/     # Analysis tools
├── utils/             # Utility functions and classes
├── assets/            # Static resources
├── files/            # Data files
└── tests/            # Test suite
```

### Development Workflow

1. Create feature branch:
   ```bash
   git checkout -b feature/new-feature
   ```

2. Make changes and test:
   ```bash
   # Run tests
   pytest tests/
   
   # Start development server
   panel serve explorer.py --autoreload
   ```

3. Submit pull request:
   - Fork repository
   - Push changes
   - Create PR with description

### Coding Standards

- Follow PEP 8 style guide
- Add docstrings (NumPy format)
- Write unit tests
- Update documentation

### Testing

Run test suite:
```bash
pytest tests/
```

Test coverage:
```bash
pytest --cov=./ tests/
```

## Troubleshooting Guide

### Common Issues

1. **Installation Problems**
   - Dependency conflicts
   - Python version mismatch
   - Missing system libraries

   Solution: Check versions, use conda-forge channel

2. **Import Errors**
   - Missing packages
   - Version incompatibilities
   - Path issues

   Solution: Verify environment, check imports

3. **Runtime Errors**
   - Memory issues
   - Performance problems
   - Display errors

   Solution: Monitor resources, check logs

4. **Data Loading Issues**
   - File format problems
   - Permission errors
   - Corrupt files

   Solution: Verify file integrity, check formats

### Performance Optimization

1. **Memory Management**
   - Use chunked loading
   - Clear unused data
   - Monitor memory usage

2. **Speed Improvements**
   - Enable caching
   - Optimize computations
   - Use efficient algorithms

3. **Display Performance**
   - Limit plot sizes
   - Use appropriate renderers
   - Optimize updates

### Getting Help

1. **Documentation**
   - Read the docs
   - Check examples
   - Review tutorials

2. **Support Channels**
   - GitHub Issues
   - Email support
   - Slack channel

3. **Debugging**
   - Check logs
   - Use debugger
   - Print statements

## License and Credits

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

### Credits

- **Stingray Library**: Core timing analysis functionality
- **Panel/HoloViz**: Interactive visualization framework
- **Contributors**: See [GitHub contributors page](https://github.com/kartikmandar-GSOC24/StingrayExplorer/graphs/contributors)

### Acknowledgments

- The Stingray development team
- HoloViz community
- X-ray astronomy community
- Google Summer of Code program
