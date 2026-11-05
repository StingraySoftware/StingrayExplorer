Saved analysis projects
=======================

A project (``.srproj``) saves a whole workspace so that it can be reopened in a
later session or on another machine.

Saving
------

Save from **Utilities → I/O Functionality → Analysis projects**, or with the
*Save analysis project* button in the header, which also records the current
page so that reopening returns to it.

A project contains:

* the loaded event lists and light curves, the spectra, and other stored
  analysis objects;
* the latest successful QuickLook result of each analysis, with the settings it
  was run with and its original record;
* selected inputs, unsent form edits (including incomplete values), tabs, plot
  scales and zoom ranges, theme and layout.

Native file grants and credentials are never saved.

Saving never overwrites an existing file. New projects are versioned ZIP64
archives: scientific arrays are stored losslessly as NumPy arrays with SHA-256
checksums, so they are not limited in size or expanded into base64 text. No
pickle or other executable format is used.

Reopening
---------

Reopening checks the whole archive before it allocates any scientific array,
and checks that enough memory is available. The project is then added in one
step, and conflicting object names are refused. To reopen a project into an
empty workspace, restart the backend first.

Reopened results keep their original scientific IDs and records. They are
shown read-only: new calculations use the current Stingray, and may differ from
the saved ones.

Older projects
--------------

Projects from every supported Stingray release can be reopened, and older v1
JSON projects remain readable. Unknown, pre-release, development and locally
modified Stingray versions are refused before anything is decoded.

When a project comes from a different Stingray release, reopening keeps the
saved arrays, identities and records exactly as they were. Defaults that the
older release did not record are added without recomputing or replacing any
saved value, and a compatibility receipt reports both versions. The migration
history survives saving the project again.

Extended-precision arrays keep their original bytes and floating-point format.
A portable 64-bit copy is stored as well, when every value fits exactly in 64
bits. A reader with the same format restores the original type; other readers
use the exact copy. If a value needs precision the reader does not have, it
fails clearly before importing anything.

Projects saved before this floating-point record existed keep their original
reading behaviour, but moving their extended-precision arrays to a machine
with a different number format is not certified. Re-save such a project with
the current application on its original machine before moving it.

If an object has an attribute that cannot be saved, saving fails with an
explanation rather than leaving the attribute out.
