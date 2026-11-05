Installation
============

Stingray Explorer currently runs from a source checkout. Signed installers are
planned but not yet published.

Requirements
------------

* `Pixi <https://pixi.sh/>`_, which installs Python, Stingray and the rest of
  the scientific stack from conda-forge. The same environment also provides
  Node.js.
* `Git LFS <https://git-lfs.com/>`_, for the sample data under ``files/data/``
  and the application images.

Set up a checkout
-----------------

.. code-block:: bash

   git lfs install
   git clone https://github.com/StingraySoftware/StingrayExplorer.git
   cd StingrayExplorer
   pixi install
   npm install
   npx install-electron

``npm install`` does not download the Electron binary; ``npx install-electron``
does.

Start the application
---------------------

.. code-block:: bash

   npm run dev

Electron starts the Python service itself, on a free loopback port, with
credentials created for that launch. Starting the service by hand as a separate
process is not supported, because it could not share those credentials or the
file permissions granted through native dialogs.

On Linux systems where Chromium's sandbox cannot start, use
``npm run dev:linux``.

Sample data
-----------

``files/data/`` holds small example files for trying the application:

* ``monol_testA.evt`` and its calibrated variants are small simulated event
  lists;
* ``lcurveA.fits`` is a binned light curve;
* ``xte_test.evt.gz`` and ``xte_gx_test.evt.gz`` are small RXTE-format event
  lists.

``files/data/DATA_README.txt`` describes every file, including the 2.4 GB
NICER observation of MAXI J1820+070 used in the Stingray tutorials, which is
not tracked and can be downloaded from https://zenodo.org/record/6785435.
