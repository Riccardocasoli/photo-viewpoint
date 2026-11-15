"""Bindings shared by QGIS 3 (Qt 5) and QGIS 4 (Qt 6)."""
from qgis.PyQt.QtCore import QT_VERSION, QMetaType
from qgis.core import Qgis

if QT_VERSION >= 0x060000:
    from qgis.PyQt.QtGui import QAction

    FIELD_STRING = QMetaType.Type.QString
    FIELD_DOUBLE = QMetaType.Type.Double
else:
    from qgis.PyQt.QtCore import QVariant
    from qgis.PyQt.QtWidgets import QAction

    FIELD_STRING = QVariant.String
    FIELD_DOUBLE = QVariant.Double

if hasattr(Qgis, 'WkbType'):
    WKB_POINT = Qgis.WkbType.Point
    GEOMETRY_LINE = Qgis.GeometryType.Line
else:
    from qgis.core import QgsWkbTypes

    WKB_POINT = QgsWkbTypes.Type.Point
    GEOMETRY_LINE = QgsWkbTypes.GeometryType.LineGeometry

if hasattr(Qgis, 'DistanceUnit'):
    DISTANCE_METRES = Qgis.DistanceUnit.Meters
    LAYOUT_MM = Qgis.LayoutUnit.Millimeters
    RENDER_MAP_UNITS = Qgis.RenderUnit.MapUnits
else:
    from qgis.core import QgsUnitTypes

    DISTANCE_METRES = QgsUnitTypes.DistanceUnit.DistanceMeters
    LAYOUT_MM = QgsUnitTypes.LayoutUnit.LayoutMillimeters
    RENDER_MAP_UNITS = QgsUnitTypes.RenderUnit.RenderMapUnits


def mouse_position(event):
    """Return an integer canvas pixel position on both Qt versions."""
    return event.position().toPoint() if QT_VERSION >= 0x060000 else event.pos()


def enum_value(flag):
    """Qt 6 enums are not always integers; some APIs still take an int."""
    return flag.value if hasattr(flag, 'value') else int(flag)
