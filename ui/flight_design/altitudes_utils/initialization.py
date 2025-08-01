from qgis.core import QgsCoordinateReferenceSystem
from ....error_reporting import QgsMessBox
from ...terrain_utils import is_poligon_inside_raster
from PyQt5.QtWidgets import QApplication

def initialize_crs_and_progressbar(ui):
    if ui.DTM and ui.DTM.crs().isValid():
        ui.crs_rst = ui.DTM.crs()
    else:
        ui.crs_rst = QgsCoordinateReferenceSystem(ui.epsg_code)
        QgsMessBox('DTM CRS Error', f'Your DTM did not have CRS.\n{ui.epsg_code} set.')

    ui.pushButtonRunDesign.setEnabled(False)
    ui.progressBar.setValue(0)
    ui.progressBar.setFormat("%p%")
    ui.progressBar.setRange(0, 100)


def initialize_design_environment(ui):
    ui.progressBar.setFormat("Initializing")
    QApplication.processEvents()
    initialize_crs_and_progressbar(ui)

    if ui.tabBlock:
        is_poligon_inside_raster(ui.AreaOfInterest, ui.DTM)
    elif ui.tabCorridor:
        is_poligon_inside_raster(ui.pathLine, ui.DTM)
    ui.pushButtonCancelDesign.setVisible(True)
    ui.progressBar.setFormat("%p%")
    ui.progressBar.setValue(0)