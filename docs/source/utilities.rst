Utilities
=========

The **Utilities** section collects Stingray's general-purpose tools.

Statistical Functions
   Convert a tail probability to an equivalent Gaussian significance, apply a
   trial correction, and evaluate probabilities and detection levels for power
   spectra, Z\ :sup:`2`\ :sub:`n` searches, epoch folding and phase dispersion
   minimisation. Probabilities too small for a floating-point number are kept
   as natural logarithms, so the significance is not lost.

GTI Functionality
   Check, merge, cross and append GTI lists; find bad time intervals and large
   gaps; build GTI masks; split GTIs by exposure; and turn GTIs into time
   intervals. Manual GTI inputs use 64-bit floating point on every platform, so
   results do not depend on the machine's extended precision.

I/O Functionality
   *File inspector* reads a file's structure and header. *RMF utilities* reads
   a response matrix and converts PI channels to energies. *Export /
   conversion* writes stored products to files (see below). *Analysis
   projects* saves and reopens ``.srproj`` projects (see :doc:`projects`).

Mission Specific I/O
   Read a mission's information and apply its event interpretation and rough
   PI-to-energy conversion.

Misc
   Helpers from ``stingray.utils``: linear and logarithmic rebinning, window
   functions, ALS baselines, equal-count energy ranges, optimal bin times,
   rounding a segment to whole samples, the nearest power of two, Poisson
   symmetrical errors and standard errors.

Exporting results
-----------------

General I/O is the only export path. Event lists, light curves and spectra can
be exported as ECSV, JSON, FITS, CSV and, where available, HDF5. Every export:

* asks for the destination through the native save dialog and refuses to
  overwrite an existing file by accident;
* is bound to the selected result's ID, so a reused name cannot export a
  different product;
* is verified in its own format before it is published.

ECSV, JSON, FITS and HDF5 carry the result's identity and calculation record.
CSV keeps the numeric columns and says explicitly that the metadata is lost.
Complex spectra are exported with real and imaginary parts as well as
magnitude and phase, and keep frequency bin widths and averaging information.
Dynamical (two-dimensional) spectra are listed with an explanation when
tabular export is not available for them.
