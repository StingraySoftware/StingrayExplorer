Analysis pages
==============

The **QuickLook** section has one page per analysis. Each page has sensible
defaults, keeps its Run button disabled until the inputs are valid, and shows
Stingray's warnings next to the result.

Pages
-----

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Page
     - What it computes
   * - Event List
     - A summary of a loaded event list: times, energies, GTIs and metadata.
   * - Light Curve
     - A binned light curve from an event list (``EventList.to_lc``), with
       rebinning and GTI handling.
   * - Power Spectrum
     - ``Powerspectrum`` of a light curve, in Leahy, fractional rms, absolute
       rms or no normalisation, with linear or logarithmic rebinning.
   * - Avg Power Spectrum
     - ``AveragedPowerspectrum.from_lightcurve`` over fixed-length segments.
   * - Cross Spectrum
     - ``Crossspectrum.from_events`` between two event lists or two bands.
   * - Avg Cross Spectrum
     - ``AveragedCrossspectrum.from_events`` over fixed-length segments.
   * - Dynamical Power Spectrum
     - ``DynamicalPowerspectrum``: power against frequency and time. Long
       calculations can run as a cancellable background job.
   * - Coherence
     - Raw coherence of an averaged cross spectrum, bias-corrected with the
       number of averaged spectra.
   * - Time Lags
     - Time lag against frequency (``AveragedCrossspectrum.time_lag``), with
       uncertainties.
   * - Cross Correlation, Auto Correlation
     - ``CrossCorrelation`` and ``AutoCorrelation`` of light curves.
   * - Dead Time Corrections
     - The Zhang et al. model correction of a power spectrum, and the Fourier
       Amplitude Difference (FAD) correction from two independent detectors.
   * - Bispectrum
     - ``Bispectrum`` of a light curve.
   * - Power Colors
     - Per-segment power colours following Heil, Uttley & Klein-Wolt (2015);
       see :doc:`science`.
   * - Covariance Spectrum, Avg Covariance Spectrum
     - ``CovarianceSpectrum`` against a reference band.
   * - RMS, Lag and Excess Variance Spectra
     - ``RmsSpectrum``, ``LagSpectrum`` and ``ExcessVarianceSpectrum``:
       variability against energy.
   * - Variable Energy Spectrum
     - Counts, fractional rms and lag against energy, from one set of
       parameters.

The **Modeling** (Model Builder, MLE and MCMC fitting), **Pulsar** (period
search, phase folding, phaseogram) and **Simulator** pages are placeholders for
work that is still planned.

Results
-------

Every result has a unique ID, the ID of the backend session that made it, and a
frozen record of its inputs and of the settings you asked for and the settings
actually used (for example a segment length rounded to whole bins). Editing the
form, or a later failed run, never relabels a plot already on screen.

Rebinning or deriving a product makes a new result that names its parent; it
never overwrites the original, and a stored name cannot silently be reused.

*Send to* passes a result to the next step. A light curve can go to the power
spectrum or averaged power spectrum pages, and a power spectrum to the averaged
or dynamical pages.

Background jobs
---------------

Calculations that can take minutes run in a separate worker process. The job
panel shows progress and, where available, a preview of partial results. A job
can be cancelled at any time; cancelling stops the worker and every process it
started, and the job is shown as *cancelled*, not as failed. Each worker runs
under a memory limit, so a calculation that grows too large is stopped instead
of exhausting the machine.

After a backend restart
-----------------------

Plots that were on screen stay visible but are marked read-only, and any action
that needs the backend asks for a current result. To keep a workspace between
launches, save it as a project (see :doc:`projects`).
