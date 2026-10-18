# Publication status and handover

0.6.0 is an experimental installable build with source and homepage materials.
It is not an approved public QGIS repository release. Maintainer metadata now
points to https://github.com/Riccardocasoli/photo-viewpoint and uses
casoli@risorsaterra.it as the public contact. The README is the initial homepage.
The repository content and any releases must still be uploaded by the maintainer.

1. Create the GitHub repository under the maintainer's account and upload this
   folder's contents as the repository root. Keep the plugin Python package name
   prese_fotografiche for upgrade compatibility.
2. Enable GitHub Pages from /docs. Customize the homepage with real repository,
   issue and download links after those exist. No external publishing was performed.
3. Review the GPL license, AI-development credit and human maintainer attribution.
4. Run all Python tests and desktop tests on supported QGIS versions and OSes;
   especially new empty dataset creation, writing/reopening edits, Shapefile
   metadata field persistence, layouts, translation and damaged/missing EXIF.
5. Capture a real demo screenshot without personal coordinates or private photos
   and add it to docs. This draft has no fabricated screenshots or user counts.
6. Build with `python tools/package.py --release` using the committed metadata.
   Experimental stays True until the maintainer has evidence for a stable release.
7. Read the current QGIS plugin validation and approval policies, sign in to the
   official plugin portal with the maintainer's account, and submit the ZIP for review.
   A successful build does not imply acceptance.

Official guidance:
- https://docs.qgis.org/3.44/en/docs/pyqgis_developer_cookbook/plugins/plugins.html
- https://plugins.qgis.org/docs/publish
- https://plugins.qgis.org/docs/approval

Before submission, review whether the minimum supported QGIS version should be
raised to the oldest version actually tested. Do not claim QGIS 4 compatibility
until API and Qt 6 support have been implemented and verified.
