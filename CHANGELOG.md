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
