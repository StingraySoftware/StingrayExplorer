Development
===========

Repository layout
-----------------

.. code-block:: text

   electron/          Main process, preload bridge and backend lifecycle
   python-backend/    FastAPI service: main.py, routes/, services/, models/, tests/
   src/               React renderer: api/, pages/, components/, hooks/, utils/
   scripts/           Compatibility, platform and repository checks
   ci/                Pinned dependency sets for continuous integration
   files/data/        Small sample data (Git LFS)
   resources/         Application icons and packaging resources
   docs/              This documentation, plans and validation records

The renderer is organised as ``src/pages/<Section>/<Page>`` (Data Ingestion,
QuickLook, Utilities, Modeling, Pulsar), with typed API modules in ``src/api``
and shared components in ``src/components``.

How the parts talk
------------------

Electron starts the Python service on a free loopback port and passes it two
per-launch secrets: a session secret that every request must carry, and a key
for signing file grants. The renderer never sees a file path chosen in a native
dialog; it receives a short-lived signed grant and sends that instead.

Service errors follow three conventions:

* errors caused by the data, such as a selection that keeps no photons, return
  HTTP 422 through a dedicated exception and a global handler;
* other service errors return HTTP 200 with ``success: false`` and a message;
* malformed requests get HTTP 422 from request validation.

Adding an analysis
------------------

Every feature follows the same pattern:

1. A service method calls Stingray directly, collects its warnings, and returns
   a result with an identity, a record of its inputs and its effective
   settings.
2. A Pydantic request model validates the inputs and their ranges.
3. A route runs the work in a worker thread, or in the job runner when it can
   take minutes (``services/job_manager.py``).
4. A typed API module in ``src/api`` exposes the route to the renderer.
5. A page or panel provides defaults, stays disabled until its inputs are valid,
   and shows warnings inline.
6. The result kind is registered in ``services/result_registry.py``, which
   decides how it is stored, saved to and reopened from ``.srproj`` projects,
   exported, and plotted by default.
7. Backend tests compare the numbers with a direct Stingray call on synthetic
   data with a known answer, such as an injected 5 Hz QPO or a 0.5 s lag.
   Renderer tests use the existing mocked-API pattern.

Every route that reads an event list must accept the optional photon selection,
or be listed as exempt, with a reason, in the every-route selection test.

The project format must stay backward compatible: the project-compatibility
tests and the pre-registry project fixture must keep passing.

Tests must check what the installed Stingray can actually do, through a
capability probe, rather than assume it.

Checks
------

Run all of these before committing:

.. code-block:: bash

   pixi run -e dev pytest python-backend/tests -q
   npx vitest run
   npm run typecheck
   npm run lint
   pixi run -e dev ruff check python-backend scripts
   npm run build

See :doc:`compatibility` for running the backend suite under other Stingray
releases.

Version
-------

``package.json`` is the only place the application version is declared.
Electron reports it with ``app.getVersion()`` and passes it to the backend in
``STINGRAY_EXPLORER_VERSION``; this documentation reads it from
``package.json`` when it is built. ``pyproject.toml`` holds tool configuration
only, and ``pixi.toml`` declares the Python environment.

Repository rules
----------------

* ``files/data/*.evt`` and ``*.fits``, and ``assets/images/*.png``, are stored
  with Git LFS.
* ``AI_DOCS/`` and ``.claude/`` are local only. They are ignored, and CI fails
  if anything under them is tracked (``scripts/check_repository_hygiene.py``).

Building this documentation
---------------------------

.. code-block:: bash

   python -m pip install -r docs/requirements.txt
   sphinx-build -W -b html docs/source docs/build/html

History
-------

The original Panel web application was retired because it accepted
browser-controlled local paths, arbitrary download URLs and unsafe
serialisation formats. Its source is preserved at the ``panel-final`` tag.
