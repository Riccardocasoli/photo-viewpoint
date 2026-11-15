## 0.7.7

- Qualify five legacy QGIS enum names flagged by the Qt 6 checker.

# 0.7.6 (experimental)

- Follow the QGIS interface language for plugin commands and dialogs, with an English fallback.
- Embed icons and localized screenshots in both HTML manuals.

# 0.7.5 (experimental)

- Place Layout Photos before Close in the layout menu.
- Clarify the layer creation command.
- Add original button icons, dialog screenshots and two separate animated workflow guides to the bilingual documentation.

# 0.7.4 (experimental)

- Preview local photos on hover without activating a map tool.
- Temporarily suspend the active photo layer’s native tips while the thumbnail is displayed.
- Use standard designer menu and toolbar, with a fallback in the main plugin menu.

# 0.7.3 (experimental)

- Keep the photo thumbnail visible while the pointer remains over the same viewpoint.
- Add Layout Photos to the print-layout menu and display the toolbar when supported.

# 0.7.2 (experimental)

- Preserve live photo frame positions and sizes on update, with layer fields as a fallback for missing frames.
- Refresh only the selected map and layer.
- Open Layout Photos from the print layout toolbar.

# 0.7.1 (experimental)

- Hover photo tips while the Photo preview tool is active.
- Select and order caption fields, set typography, alignment and background opacity.
- Remember caption settings per layout map and viewpoint layer.

# 0.7.0 (experimental)

- Adapt Qt bindings for QGIS 4 while retaining QGIS 3.
- Preserve field names in SQLite exports.
- Add a shared desktop smoke test runner.

# 0.6.1

Preserve case-sensitive QGIS metadata keys and use Riccardo Casoli as author.
Installable releases omit development tests and build tools; these remain in the
source repository. Optional-operation failures are logged at debug level.
No viewpoint geometry or editing behavior changes.

# Changelog

## 0.6.0 — experimental
- New English code/caption schema, table ordering and non-destructive legacy compatibility.
- Long caption capacity outside DBF limitations; English-only plugin UI.
- Apply viewpoint style dialog with four embedded/native presets and sizes.
- QML persistence and GeoPackage/SQLite default-style attempt with reported fallback.
- English-field GeoPackage copy and complete English/Italian manuals.


## 0.5.0 — experimental
- Batch image import with EXIF position and true-north-to-grid bearing conversion.
- No-GPS rows can be excluded before import or kept with NULL geometry for manual placement.
- Pending-photo dock and reversible deletion of records, never image files.
- Visible defaults (0°, 40°, 20 m), paired creation icons, distGPS and vp_status defaults.
- Source GPS attributes are not overwritten by geometric edits.


## 0.4.0 — experimental
- New unified layer creation dialog: CRS, English default name, temporary storage
  or a new GeoPackage/Shapefile/SQLite/FlatGeobuf file, project directory default.
- Bounded JPEG/TIFF EXIF reader, independent metadata fields, automatic refresh
  when linking/replacing images, and explicit refresh for existing features.
- English/Italian UI, English metadata/README and a static GitHub Pages homepage.
- Full GPL license, packaging/release validator and standard-library test workflow.
- No live GitHub repository or official QGIS approval implied.

## 0.3.0
Per-image aspect ratio, max dimensions, persisted dimX/dimY and Didascalia,
free overlap in layouts.

## 0.2.0
Layout images, point callouts, free positioning and saved page coordinates.

## 0.1.0–0.1.6
Three-click capture, labels, editable handles, image links/preview and icons.
