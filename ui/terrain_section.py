from math import ceil, fabs
from qgis.core import (
    QgsRectangle,
    QgsVectorLayer,
    QgsRasterLayer,
)
from qgis.analysis import QgsZonalStatistics
from qgis import processing
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMessageBox
from pyproj import Transformer
from ..utils import show_error, transf_coord


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
        """Oblicza min/max DTM dla aktualnie wybranego trybu (blok / korytarz)."""
        if self.dtm is None:
            QMessageBox.warning(self.dlg, "DTM needed",
                                "You have to load a valid DTM layer.")
            return

        if self.dlg.tabBlock:
            if self.aoi is None:
                QMessageBox.warning(self.dlg, "AoI needed",
                                    "You have to load a valid Area‑of‑Interest layer.")
                return
            vector_for_stats = self.aoi

        else:
            if self.path_line is None:
                QMessageBox.warning(self.dlg, "Corridor line needed",
                                    "You have to load a Corridor line layer.")
                return
            try:
                vector_for_stats = self._create_buffer_around_line()
            except Exception as e:
                QMessageBox.critical(self.dlg, "Buffer creation failed", str(e))
                return

        try:
            h_min, h_max = self._minmaxheight(vector_for_stats)
            self.dlg.doubleSpinBoxMinHeight.setValue(h_min)
            self.dlg.doubleSpinBoxMaxHeight.setValue(h_max)
        except Exception as e:
            QMessageBox.critical(self.dlg, "Error",
                                 f"Failed to get heights from DTM:\n{e}")
            show_error()

    def _create_buffer_around_line(self) -> QgsVectorLayer:
        """Zwraca warstwę bufora linii o minimalnej szerokości 1 piksel rastra."""
        gt = self.gdal_ds.GetGeoTransform()
        px_w, px_h = gt[1], -gt[5]
        ulx, uly = gt[0], gt[3]
        ulx_n, uly_n = ulx + px_w, uly + px_h

        crs_rst = self.dtm.crs().authid()
        crs_vec = self.path_line.sourceCrs().authid()
        if crs_rst != crs_vec:
            tf = Transformer.from_crs(crs_rst, crs_vec, always_xy=True)
            ulx, uly = transf_coord(tf, ulx, uly)
            ulx_n, uly_n = transf_coord(tf, ulx_n, uly_n)

        min_buf = max(ceil(fabs(ulx_n - ulx)), ceil(fabs(uly_n - uly)))
        self.dlg.doubleSpinBoxBuffer.setMinimum(min_buf / 2)

        params = {
            "INPUT": self.path_line,
            "DISTANCE": self.dlg.doubleSpinBoxBuffer.value(),
            "SEGMENTS": 5,
            "END_CAP_STYLE": 0,
            "JOIN_STYLE": 0,
            "MITER_LIMIT": 2,
            "DISSOLVE": False,
            "OUTPUT": "TEMPORARY_OUTPUT",
        }
        out = processing.run("native:buffer", params)["OUTPUT"]
        return out

    def _filter_features_inside_raster(self, vlayer) -> list:
        """Zwraca featury w całości mieszczące się w zasięgu rastra."""
        r_extent: QgsRectangle = self.dtm.extent()
        return [f for f in vlayer.getFeatures()
                if r_extent.contains(f.geometry().boundingBox())]

    def _minmaxheight(self, vlayer) -> tuple[float, float]:
        """Globalne min/max rastra w obrębie geometrii `vlayer`."""
        feats = self._filter_features_inside_raster(vlayer)
        if not feats:
            raise ValueError("No vector features lie entirely within the raster extent.")

        temp = QgsVectorLayer(f"Polygon?crs={vlayer.crs().authid()}",
                              "temp", "memory")
        temp.dataProvider().addFeatures(feats)
        temp.updateExtents()

        stats = QgsZonalStatistics(
            temp, 
            self.dtm,
            "pre_",
            1,
            QgsZonalStatistics.Min | QgsZonalStatistics.Max
        )
        if stats.calculateStatistics(None) != 0:
            raise RuntimeError("Zonal statistics calculation failed.")

        gmin, gmax = None, None
        for f in temp.getFeatures():
            try:
                mn, mx = float(f["pre_min"]), float(f["pre_max"])
                gmin = mn if gmin is None or mn < gmin else gmin
                gmax = mx if gmax is None or mx > gmax else gmax
            except Exception:
                continue

        if gmin is None or gmax is None:
            raise ValueError("Could not determine min/max values from raster.")
        return gmin, gmax
