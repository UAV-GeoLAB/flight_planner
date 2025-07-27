import os
from .....utils import QgsTraceback, QgsPrint
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
)
from pyproj import Transformer

from .....functions import (
    create_flight_line,
    create_waypoints,
    change_layer_style,
    transf_coord,
    minmaxheight
)


class Worker(QObject):
    """Worker dla trybu 'Separate Altitude ASL For Each Strip'."""

    finished = pyqtSignal(object, str)
    error = pyqtSignal(Exception, str)
    progress = pyqtSignal(int)
    enabled = pyqtSignal(bool)

    def __init__(self, **data):
        super().__init__()
        self.layer = data.get('pointLayer')
        self.crs_vct = data.get('crsVectorLayer')
        self.DTM = data.get('DTM')
        self.raster = data.get('raster')
        self.layer_pol = data.get('polygonLayer')
        self.crs_rst = data.get('crsRasterLayer')
        self.altitude_AGL = data.get('altitude_AGL')
        self.tab_widg_cor = data.get('tabWidg')
        self.g_line_list = data.get('LineRangeList')
        self.geom_aoi = data.get('Range')
        self.theta = data.get('theta')
        self.dist = data.get('distance')
        self.start_progress = data.get('start_progress', 0)
        self.killed = False

    def run_altitudeStrip(self):
        result = []
        try:
            strips_count = int(self.layer.maximumValue(0))
            progress_c = 0
            step = int(strips_count // 1000)
            feat_strip = QgsFeature()

            if self.crs_rst != self.crs_vct:
                transf_vct_rst = Transformer.from_crs(
                    self.crs_vct, self.crs_rst, always_xy=True
                )

            for t in range(1, strips_count + 1):
                if self.killed:
                    self.handle_cancel()
                    return

                strip_nr = f"{t:04d}"
                feats = self.layer.getFeatures(f'"Strip" = \'{strip_nr}\'')
                nrP_max = 0
                nrP_min = 1000000
                BuffNr = None

                for f in feats:
                    if self.killed:
                        self.handle_cancel()
                        return
                    num = int(f.attribute('Photo Number'))
                    nrP_max = max(nrP_max, num)
                    nrP_min = min(nrP_min, num)
                    if self.tab_widg_cor:
                        BuffNr = int(f.attribute('BuffNr'))

                photos_list = [
                    f.attributes()[:2] + [f.id(), f.geometry()]
                    for f in self.layer_pol.getFeatures()
                ]
                photos_list.sort(key=lambda x: x[1])
                strip_photos = [f for f in photos_list if int(f[0]) == t]

                if not strip_photos:
                    continue

                first_photo = strip_photos[0][-1].asPolygon()[0]
                last_photo = strip_photos[-1][-1].asPolygon()[0]
                points = first_photo + last_photo

                x_pnt = np.array([p.x() for p in points]).reshape(-1, 1)
                y_pnt = np.array([p.y() for p in points]).reshape(-1, 1)
                pnts = np.hstack((x_pnt, y_pnt))

                pnt1 = pnts[np.argmin(pnts[:, 0])]
                pnt2 = pnts[np.argmin(pnts[:, 1])]
                pnt3 = pnts[np.argmax(pnts[:, 0])]
                pnt4 = pnts[np.argmax(pnts[:, 1])]

                one_strip = [
                    QgsPointXY(pnt1[0], pnt1[1]),
                    QgsPointXY(pnt2[0], pnt2[1]),
                    QgsPointXY(pnt3[0], pnt3[1]),
                    QgsPointXY(pnt4[0], pnt4[1])
                ]
                g_strip = QgsGeometry.fromPolygonXY([one_strip])
                kappa = float(f.attribute('Kappa [deg]'))
                if kappa in [-90, 0, 90, 180]:
                    g_strip = QgsGeometry.fromPolygonXY([points])
                    g_strip = QgsGeometry.fromRect(g_strip.boundingBox())

                if self.tab_widg_cor:
                    common = g_strip.intersection(self.g_line_list[BuffNr - 1])
                    if common.isEmpty():
                        QgsPrint(f"Strip {t}: Intersection with g_line_list[{BuffNr - 1}] is empty, używam g_strip zamiast intersection.")
                        common = g_strip
                else:
                    common = g_strip.intersection(self.geom_aoi)
                    if common.isEmpty():
                        QgsPrint(f"Strip {t}: Intersection with geom_aoi is empty, używam g_strip zamiast intersection.")
                        common = g_strip

                feat_strip.setGeometry(common)
                common_lay = QgsVectorLayer("Polygon?crs=" + str(self.crs_vct), "row", "memory")
                prov_com = common_lay.dataProvider()
                prov_com.addFeature(feat_strip)

                h_min, h_max = minmaxheight(common_lay, self.DTM)
                avg_terrain_height = h_max - (h_max - h_min) / 3
                altitude_ASL = self.altitude_AGL + avg_terrain_height

                self.layer.startEditing()
                for k in range(nrP_min, nrP_max + 1):
                    if self.killed:
                        self.handle_cancel()
                        return
                    photo_nr = f"{k:05d}"
                    ph_nr_iter = self.layer.getFeatures(f'"Photo Number" = \'{photo_nr}\'')
                    for f in ph_nr_iter:
                        ph_nr = f.id()

                        x = f.geometry().asPoint().x()
                        y = f.geometry().asPoint().y()
                        if self.crs_rst != self.crs_vct:
                            x, y = transf_coord(transf_vct_rst, x, y)

                        terrain_height, _ = self.DTM.dataProvider().sample(QgsPointXY(x, y), 1)
                        altitude_AGL = altitude_ASL - terrain_height

                        self.layer.changeAttributeValue(ph_nr, 5, round(altitude_AGL, 2))
                        self.layer.changeAttributeValue(ph_nr, 4, round(altitude_ASL, 2))
                self.layer.commitChanges()

                progress_c += 1
                if step == 0 or progress_c % step == 0:
                    progress_value = self.start_progress + int(progress_c / strips_count * (100 - self.start_progress))
                    self.progress.emit(progress_value)

            waypoints_layer = create_waypoints(self.layer, self.crs_vct)
            waypoints_layer.setCrs(self.crs_vct)

            if not self.killed:
                self.progress.emit(100)
                flight_line = create_flight_line(waypoints_layer, self.crs_vct)
                flight_line.setCrs(self.crs_vct)

                style_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'altitudes_utils',
                    'flight_line_style.qml'
                )
                flight_line.loadNamedStyle(style_path)

                if self.tab_widg_cor:
                    self.layer.startEditing()
                    self.layer.deleteAttributes([9, 10, 11])
                    self.layer.commitChanges()
                    self.layer_pol.startEditing()
                    self.layer_pol.deleteAttributes([2, 3])
                    self.layer_pol.commitChanges()

                change_layer_style(self.layer_pol, {'color': '200,200,200,30', 'color_border': '#000000', 'width_border': '0.2'})
                change_layer_style(self.layer, {'size': '1.0'})
                self.layer_pol.setName('photos')
                self.layer_pol.setCrs(self.crs_vct)
                self.layer.setName('projection centres')
                self.layer.setCrs(self.crs_vct)

                result.extend([self.layer, flight_line, waypoints_layer, self.layer_pol])
        except Exception as e:
            import traceback
            self.error.emit(e, traceback.format_exc())
            self.progress.emit(0)
            self.enabled.emit(True)
            return
            
        self.finished.emit(result, "flight_design")
        self.enabled.emit(True)

    def handle_cancel(self):
        self.progress.emit(0)
        self.enabled.emit(True)
        self.finished.emit(None, "flight_design")