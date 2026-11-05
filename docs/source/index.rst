Stingray Explorer
=================

Stingray Explorer is a desktop application for X-ray spectral-timing analysis.
It puts a graphical interface on `Stingray <https://docs.stingray.science/>`_:
you load event lists or light curves, choose photons by energy, detector and
time, and compute power spectra, cross spectra, lags, coherence, dead-time
corrections, power colours and variability-versus-energy spectra. Every result
carries a full record of how it was made, and can be saved to a project file,
reopened later and exported.

The application is built from three parts:

* an Electron desktop shell, which owns native file dialogs and starts the
  scientific service;
* a React renderer, which draws the pages and plots;
* a FastAPI service on a private loopback port, which runs Stingray.

.. toctree::
   :maxdepth: 2
   :caption: Using the application

   installation
   data
   analysis
   utilities
   projects

.. toctree::
   :maxdepth: 2
   :caption: Reference

   science
   compatibility

.. toctree::
   :maxdepth: 2
   :caption: Contributing

   development
