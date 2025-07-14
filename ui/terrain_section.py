from qgis.core import QgsRasterLayer, QgsVectorLayer
from PyQt5.QtCore import pyqtSlot

from ..utils import show_info
from .terrain_utils import create_buffer_around_line, minmaxheight


class TerrainSectionHandler:

    def __init__(self, dialog):
        self.dlg = dialog
        self.dtm: QgsRasterLayer = None
        self.aoi: QgsVectorLayer = None
        self.path_line: QgsVectorLayer = None
        self.gdal_ds = None

    def set_dtm(self, dtm_layer: QgsRasterLayer, gdal_dataset):
        self.dtm = dtm_layer
        self.gdal_ds = gdal_dataset

    def set_aoi(self, aoi_layer: QgsVectorLayer):
        self.aoi = aoi_layer

    def set_corridor_line(self, line_layer: QgsVectorLayer):
        self.path_line = line_layer

    @pyqtSlot()
    def on_btn_get_heights_clicked(self):
        if self.dtm is None:
            show_info(title="DTM needed", text="You have to load a valid DTM layer.", level="Critical")
            return

        if self.dlg.tabBlock:
            if self.aoi is None:
                show_info(title="AoI needed", text="You have to load Area-of-Interest layer.", level="Critical")
                return
            vector_for_stats = self.aoi
        else:
            if self.path_line is None:
                show_info(title="Corridor line needed", text="You have to load Corridor line layer.", level="Critical")
                return
            try:
                vector_for_stats, min_buf = create_buffer_around_line(
                    self.path_line,
                    self.gdal_ds,
                    self.dtm,
                    self.dlg.doubleSpinBoxBuffer.value()
                )
                self.dlg.doubleSpinBoxBuffer.setMinimum(min_buf / 2)
            except Exception as e:
                show_info(title="Buffer creation failed", text=str(e), level="Critical")
                return

        try:
            h_min, h_max = minmaxheight(vector_for_stats, self.dtm)
            self.dlg.doubleSpinBoxMinHeight.setValue(h_min)
            self.dlg.doubleSpinBoxMaxHeight.setValue(h_max)
        except Exception as e:
            show_info(title="Error", text=f"Failed to get heights from DTM:\n{e}", level="Critical")
