Scientific conventions
======================

These rules apply to every calculation. They exist so that a result means what
its label says.

Times and references
--------------------

* Analyses of two inputs require the same finite MJD reference and compatible
  time-system, time-reference and ephemeris metadata. Metadata known for only
  one input is refused. Metadata unknown for both is allowed, but does not
  establish a verified common time reference. Align different origins or time
  scales explicitly before the analysis.
* Paired Fourier analyses bin both inputs from a common origin, with a bin
  width compatible with both instruments' known time resolutions. The returned
  effective settings describe what was calculated, including any rounding of
  the segment length.

Good time intervals
-------------------

* GTI selections on a light curve are intersected with its own exposure, and
  only complete bins on the original grid are kept. Gaps are excluded from the
  stored product and from the mean rate.
* Correlation needs one continuous interval. Exactly adjacent intervals count
  as continuous; any positive gap is refused. Use GTI Functionality to choose a
  continuous interval before correlating a gapped observation.

Photon selections
-----------------

Energy and PI ranges are half-open, ``[lo, hi)``, so adjacent bands never share
a photon. The selection and the event counts before and after it are stored in
the result's record. See :doc:`data`.

Power colours
-------------

Power colours use noise-subtracted, integrated fractional variances, with
PC1 = C/A and PC2 = B/D as defined by
`Heil, Uttley & Klein-Wolt (2015) <https://arxiv.org/abs/1405.2024>`_, and
errors propagated in quadrature.

* The calculation assumes ideal Poisson counting noise. It does not model
  detector dead time or background.
* A ratio is reported only when both variances are positive and at least three
  propagated standard errors above zero. Other segments keep their variance
  estimates and report the ratio as null.
* These are exploratory per-segment estimates, with approximate errors for
  sparsely sampled bands. Do not read them directly as source states.

Stingray's own ``power_color`` returns the inverse ratio A/C and adds relative
errors linearly, so the application performs this small calculation itself.

Floating-point precision
------------------------

Older Stingray releases cannot build light curves from extended-precision
(``float128``) times on x86-64 Linux. The application checks this at run time;
when the installed release cannot, it uses 64-bit times and records
``time_precision: "float64"`` in the result's record.
