Loading and selecting data
==========================

Data Ingestion
--------------

The **Data Ingestion** page loads data into the current workspace. Its tabs
offer four sources:

Local File
   Event files read with Stingray's ``EventList.read``. Batch mode loads
   several files at once, and *Reselect Last Files* reopens the previous
   selection.

From URL
   A file downloaded from a URL you enter. Downloads go through a checked
   network boundary with redirect, time and size limits; local and private
   network addresses are refused.

Browse HEASARC
   Search the HEASARC archive and load an observation's event files.

Light Curve
   A binned light curve from a FITS table: NICER, Swift-XRT, RXTE and generic
   OGIP files. The loader respects ``TIMEZERO``, ``MJDREF``, ``TIMEUNIT``, GTI
   extensions, fractional exposure and error columns. A file in days without
   ``MJDREF`` loads with relative times. A file in seconds without ``MJDREF``
   asks you for the reference epoch.

Files are always chosen through the operating system's file dialog. The
renderer never sends a typed path to the scientific service; it sends a
short-lived grant that names the file you chose.

After loading, the preview tabs show the event list's overview, time data,
energy and PI columns, GTIs, metadata, the FITS header and validation results.

Photon selections
-----------------

Most analysis pages accept a *photon selection* for each input event list. A
selection can combine:

* an energy range in keV, or a PI channel range (one or the other);
* a list of detector IDs;
* time intervals;
* an extra GTI list, intersected with the file's own GTIs.

Ranges are half-open, ``[lo, hi)``, the same convention as Stingray's
``get_energy_mask``, so adjacent bands never share a photon.

The selection field offers band presets for NuSTAR, NICER, RXTE, XMM-Newton,
Chandra and Swift, a set of common bands, and bands you save yourself. A live
preview shows how many events the selection keeps before you run anything.

A selection is applied to a private copy of the event list; the loaded data is
never changed. The result's record stores the exact selection and the event
counts before and after it, and that record survives saving and reopening a
project.

Two-band analyses
~~~~~~~~~~~~~~~~~

Cross Spectrum, Averaged Cross Spectrum, Time Lags, Coherence and Cross
Correlation accept a separate selection for each band, and both bands may come
from the same event list. When the two bands share photons, the page warns you
and reports how many photons they share.

Where selections are restricted
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Power colours use a single band.
* The energy-resolved spectra (rms, lag, covariance, excess variance and
  variable-energy) set their own energy bins, so they accept detector, time and
  GTI cuts but refuse an energy cut.
* The Fourier Amplitude Difference (FAD) dead-time correction needs two
  independent detectors, each with its own selection. Two bands from one
  detector are refused, because they share that detector's dead time.

Derived event lists
-------------------

A derived event list is made from loaded lists and stored next to them, marked
with a **Derived** chip and a record of its parents. Four operations are
available:

* **filter** keeps the photons a selection keeps;
* **join** merges lists into one time-ordered list, for example NuSTAR FPMA and
  FPMB;
* **sort** puts photons in time order, keeping every column aligned;
* **dead time** simulates detector dead time by removing photons that arrive
  inside a dead window.
