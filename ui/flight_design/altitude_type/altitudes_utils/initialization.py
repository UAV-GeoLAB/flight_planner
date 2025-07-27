from qgis.core import QgsCoordinateReferenceSystem
from .....utils import QgsMessBox

def initialize_crs_and_progressbar(ui):
    if ui.DTM and ui.DTM.crs().isValid():
        ui.crs_rst = ui.DTM.crs()
    else:
        ui.crs_rst = QgsCoordinateReferenceSystem(ui.epsg_code)
        QgsMessBox('DTM CRS', f'Your DTM did not have CRS. {ui.epsg_code} set.')

    ui.pushButtonRunDesign.setEnabled(False)
    ui.progressBar.setValue(0)
    ui.progressBar.setFormat("%p%")
    ui.progressBar.setRange(0, 100)