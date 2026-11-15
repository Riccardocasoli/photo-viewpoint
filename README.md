# Photo viewpoint — QGIS plugin

**Experimental 0.7.6.** Create and edit photo viewpoints in three clicks, or import
photos using available EXIF GPS. Preview original images, track displacement from
GPS and generate freely movable photo callouts in print layouts.

- [Presentation and user manual — English](docs/manual-en.html)
- [Presentazione e manuale — Italiano](docs/manual-it.html)
- [Animated demonstrations / GIF](docs/demos/index.html)
- [Static homepage source](docs/index.html)
- [Publication handover](PUBLISHING.md)

Open MANUALE.html in a browser to choose a manual. Both are printable and their images are embedded. The interface follows the QGIS language, with an English fallback. Earlier
GUIDA_0_*.md files describe historical versions; current manuals take precedence.

## What's new in 0.6

- English UI and new physical field names: **code, caption, distGPS** first,
  followed by service fields in their existing relative order.
- Caption width 2,000 for new non-Shapefile layers; width 254 for SHP/DBF, which
  cannot guarantee 255+ Unicode characters. Use GeoPackage for long captions.
- Legacy codice/Didascalia layers remain supported without destructive renaming.
  English table aliases/order and a separate English-field GeoPackage copy command
  provide a safe upgrade path. A provider's own primary key may still exist.
- **Apply viewpoint style** opens four presets: classic point/rays, oriented top-view
  camera with dashed blue rays, circle/bearing arrow without FOV, translucent sector.
- Size and code-label options. Native QGIS expressions and base64-embedded SVG
  artwork keep styles independent of plugin installation paths.
- Reusable QML sidecars on new local datasets and style application; database
  default style storage is attempted for GeoPackage/SQLite, with explicit fallback
  messages. QGIS-specific geometry generators require QML rather than SLD.

## Core workflow

Install the ZIP from QGIS Plugins → Manage and Install Plugins → Install from ZIP.
The package name stays `prese_fotografiche`, preserving the upgrade path.
Create a temporary layer or a new GeoPackage, SHP, SQLite or FlatGeobuf dataset,
select a projected CRS in metres, then use either creation icon.

Import defaults are azimuth 0°, FOV 40°, graphic length 20 m. Photos without usable
GPS may be excluded or retained as NULL-geometry records in Photos to position.
They can be located manually without fabricated coordinates. GPS metadata stays
separate from the editable geometry; distGPS is a QGIS apply-on-update planar
comparison field, not a standalone database trigger. Save layer edits AND project.

Metadata reading supports conventional JPEG APP1/TIFF EXIF without external Python
packages. No HEIC/RAW, MakerNotes, XMP-only GPS or network downloads. True-north
image direction can be converted to grid bearing; magnetic/unknown direction uses
the default. Missing values stay NULL. Originals are not modified or uploaded.

Open **Layout Photos** from the print layout toolbar or **Layout → Layout Photos**. The plugin menu in the main window also has
a fallback **Layout Photos…** command. Choose a map and
viewpoint layer. Generate / Update refreshes image links, leaders and captions
while preserving existing frame positions and sizes. Save the QGIS project to
keep the frames across sessions. The optional **Save frame positions and sizes
to layer** writes pf_x/pf_y/pf_map/dimX/dimY; commit the layer edits to retain
this backup. A missing frame can be rebuilt from those fields for the matching
map; new frames without a backup use the dialog's size and spacing settings.
The fields hold one backup per feature, not a separate backup for every map.
Static layouts in mm only; atlas and arbitrary clipping/temporal rendering
are outside this version's scope.

## Style reuse

Keep `survey.qml` with `survey.shp` or `survey.fgb`. For GeoPackage/SQLite, a
per-table QML backup is written and an internal default style is attempted.
If the provider cannot store it, load the QML from Layer Properties → Style.
Save pending edits first. A project with an existing assigned style may continue
using that style until it is reloaded. An unmodified source dataset does not
magically adopt styles from other projects without this storage or sidecar.

## Requirements and tests

Targets QGIS 3 (Qt 5) and QGIS 4 (Qt 6), with a metric projected CRS.
Automated integration checks were run on QGIS 3.40.6 / Qt 5.15.15.
Version 0.7.0 was tested by the maintainer on QGIS 4.2.3. The maintainer also confirmed the layout button and menu in 0.7.4; see [the test checklist](QGIS4_TEST.md).

From the parent directory:

```sh
python -m unittest discover -s prese_fotografiche -t . -p 'test_*.py' -v
```

Desktop smoke tests are development files retained in the source repository,
not included in the installable ZIP. To use them, work from a source checkout.

QGIS Python console:

```python
import prese_fotografiche.smoke_test_styles as styles
styles.run()
import prese_fotografiche.smoke_test_import as importing
importing.run()
```

Additional storage, basic and layout integration tests are included. The tests
use isolated temporary data. Python tests alone do not certify native rendering
or automatic style loading by providers.

## GitHub / QGIS publication

Source: https://github.com/Riccardocasoli/photo-viewpoint  
Issues: https://github.com/Riccardocasoli/photo-viewpoint/issues  
Maintainer: Riccardo Casoli — casoli@risorsaterra.it

This folder is the repository root. The README is the initial homepage;
GitHub Pages can optionally be enabled from `/docs`. Official QGIS approval
is pending. New style/schema features still require native QGIS validation.

Build an installable ZIP from the repository root:

```sh
python tools/package.py --release
```

The generated ZIP is in `dist/`. Attach it to a GitHub Release; do not commit
ZIP archives to the source repository. GitHub's automatic source archives are
not the installable QGIS package. Building does not publish or approve a plugin.

## Credits

Concept, requirements and hands-on testing: **Riccardo Casoli**. Code, original
icons and documentation assistance: **ChatGPT / Codex (OpenAI)** through iterative
collaboration. A human maintainer is required. Not an official QGIS/OpenAI product.
GPL-3.0-or-later; full text in LICENSE.

## Photo tips and layout captions

Pause over a viewpoint in the active visible photo layer for a local photo
thumbnail. Select **Open photo preview** to open the full preview on click. In **Layout photos**, check
and reorder caption fields, and choose a font, size, alignment and colors.
The filename comes from the local image path linked in `photo`. Caption
settings are stored in the project for each layout map and viewpoint layer.
