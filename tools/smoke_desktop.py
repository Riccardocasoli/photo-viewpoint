"""Run the development smoke suite in the Python console of QGIS 3 or 4.

Ensure that the source checkout is importable as prese_fotografiche.
Then run: from prese_fotografiche.tools.smoke_desktop import run; run(iface)
"""
from qgis.core import Qgis
from qgis.PyQt.QtCore import QT_VERSION_STR

from .. import (smoke_test_import, smoke_test_layout, smoke_test_qgis,
                smoke_test_storage, smoke_test_styles)


def run(iface):
    print(f'QGIS {Qgis.QGIS_VERSION}, Qt {QT_VERSION_STR}')
    smoke_test_qgis.run(iface)
    smoke_test_storage.run(iface)
    smoke_test_import.run()
    smoke_test_styles.run()
    smoke_test_layout.run()
