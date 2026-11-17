# Photo viewpoint — QGIS plugin

Photo viewpoint links field photographs to camera locations, viewing directions
and fields of view. Create viewpoints manually, import geotagged images, and add
photo callouts to QGIS print layouts.

**Current release: 0.7.8 (stable).** The preceding 0.7.6 release was tested by the maintainer on QGIS 4.2.3.
The plugin supports QGIS 3 and QGIS 4. Its interface follows the QGIS language:
Italian when selected, English otherwise.

## Install

Download [prese_fotografiche_v0.7.8.zip](https://github.com/Riccardocasoli/photo-viewpoint/releases/download/v0.7.8/prese_fotografiche_v0.7.8.zip).
In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
Select the downloaded ZIP without extracting it.

## What you can do

- Create a viewpoint in three clicks, then assign a code and link a photograph.
- Import multiple photos using EXIF GPS, and position photos without GPS manually.
- Move a viewpoint or adjust its direction, graphic length and field of view.
- Hover over a viewpoint for a thumbnail, or use the preview tool to open the
  full image, locate its folder or change the link.
- Apply styles and generate photo callouts from **Layout Photos** in the print
  layout window. Customize the caption fields, font, colors and alignment.
  Updating a layout preserves the position and size of existing photo frames.

## Manuals and demonstrations

Download or clone the repository and open the HTML manuals in a browser.
The button icons and dialog screenshots are embedded in each manual.

- [English manual](docs/manual-en.html)
- [Manuale italiano](docs/manual-it.html)
- [Animated demonstrations / GIF](docs/demos/index.html)
- [Version history](CHANGELOG.md)

## Credits and license

Concept, requirements and hands-on testing: **Riccardo Casoli**.
Code, icons and documentation assistance: **ChatGPT / Codex (OpenAI)**.

[GPL-3.0-or-later](LICENSE) · [Report an issue](https://github.com/Riccardocasoli/photo-viewpoint/issues)
