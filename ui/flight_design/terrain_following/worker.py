import os
import traceback
from math import (
    atan,
    ceil,
    cos,
    pi,
    sin,
    sqrt
)
import numpy as np
from pyproj import Transformer
from PyQt5.QtCore import QObject, QVariant, pyqtSignal
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem
)

from PyQt5.QtWidgets import QApplication

from ....mathgeo_utils.coordinates import (
    crs2pixel,
    transf_coord
)
from ...terrain_utils import z_at_3d_line, simplify_profile

from ....geoprocessing_utils.layers import create_waypoints_layer, create_flight_line, change_layer_style

class WorkerTerrain(QObject):
    """Worker for 'Terrain Following'."""
    finished = pyqtSignal(object, str)
    error = pyqtSignal(Exception, str)
    progress = pyqtSignal(int)
    enabled = pyqtSignal(bool)

    def __init__(self, **data):
        super().__init__()
        self.layer = data.get('pointLayer')
        self.crs_vct = data.get('crsVectorLayer')
        self.raster = data.get('raster')
        self.layer_pol = data.get('polygonLayer')
        self.crs_rst = data.get('crsRasterLayer')
        self.tolerance = data.get('tolerance')
        self.altitude_AGL = data.get('altitude_AGL')
        self.start_progress = data.get("start_progress", 0)
        self.epsg_code = data.get("epsg_code")
        self.killed = False
    
    def run_followingTerrain(self):
        result = []
        try:
            geotransf, DTM_array, pix_width, pix_height, diagonal_angle, transf_vct_rst, transf_rst_vct = self.prepare_raster_data()
            pr, waypoints_layer = create_waypoints_layer(self.crs_vct)
            proj_cent_list = self.group_strip_centers()

            strips_nr = int(self.layer.maximumValue(0))
            waypoint_nr = 1
            progress_c = 0
            # step = max(1, strips_nr // 1000)
            step = strips_nr // 1000
            for strip_nr in range(1, strips_nr + 1):
                if self.killed:
                    self.handle_cancel()
                    return

                QApplication.processEvents()

                strip_proj_centres = [f for f in proj_cent_list if int(f[0]) == strip_nr]
                pc_coords = np.array([(f[-1].asPoint().x(), f[-1].asPoint().y()) for f in strip_proj_centres])

                simplified_profile, pc_z = self.generate_simplified_profile(
                    pc_coords, strip_proj_centres, geotransf, DTM_array, pix_width, pix_height, diagonal_angle, transf_vct_rst
                )

                waypoint_nr = self.create_flight_profile_waypoints(
                    pc_z, simplified_profile, strip_proj_centres, DTM_array, geotransf, waypoint_nr, pr
                )
                waypoints_layer.updateExtents()
                if step == 0 or progress_c % step == 0:
                    progress_range = 100 - self.start_progress
                    progress_value = self.start_progress + int((progress_c / strips_nr) * progress_range)
                    self.progress.emit(progress_value)

                progress_c += 1

            if not self.killed:
                self.progress.emit(100)
                self.finalize_layers(waypoints_layer, result)

        except Exception as e:
            self.error.emit(e, traceback.format_exc())
            self.progress.emit(0)
            self.enabled.emit(True)
            return

        self.finished.emit(result, "flight_design")
        self.enabled.emit(True)

    def prepare_raster_data(self):
        geotransf = self.raster.GetGeoTransform()
        raster_array = self.raster.GetRasterBand(1).ReadAsArray()
        nodata = self.raster.GetRasterBand(1).GetNoDataValue()
        DTM_array = np.ma.masked_equal(raster_array, nodata)

        pix_width = geotransf[1]
        pix_height = -geotransf[5]

        if self.crs_rst != self.crs_vct:
            transf_vct_rst = Transformer.from_crs(self.crs_vct, self.crs_rst, always_xy=True)
            transf_rst_vct = Transformer.from_crs(self.crs_rst, self.crs_vct, always_xy=True)

            uplx = geotransf[0]
            uply = geotransf[3]
            uplx_n = uplx + pix_width
            uply_n = uply + pix_height

            xo, yo = transf_coord(transf_rst_vct, uplx, uply)
            xo1, yo1 = transf_coord(transf_rst_vct, uplx_n, uply_n)

            pix_width = WorkerTerrain.distance2d((xo, yo), (xo1, yo))
            pix_height = WorkerTerrain.distance2d((xo, yo), (xo, yo1))
        else:
            transf_vct_rst = transf_rst_vct = None

        diagonal_angle = atan(pix_height / pix_width) * 180 / pi

        return geotransf, DTM_array, pix_width, pix_height, diagonal_angle, transf_vct_rst, transf_rst_vct

    def group_strip_centers(self):
        feats = self.layer.getFeatures()
        proj_cent_list = [f.attributes()[:2] + [f.id(), f.geometry()] for f in feats]
        proj_cent_list.sort(key=lambda x: x[1])
        return proj_cent_list
    
    def generate_simplified_profile(self, pc_coords, strip_proj_centres, geotransf, DTM_array, pix_width, pix_height,
                                diagonal_angle, transf_vct_rst):
        first_pc = strip_proj_centres[0]
        last_pc = strip_proj_centres[-1]

        first_x = first_pc[-1].asPoint().x()
        first_y = first_pc[-1].asPoint().y()
        last_x = last_pc[-1].asPoint().x()
        last_y = last_pc[-1].asPoint().y()

        direction = 90
        if last_x - first_x != 0:
            direction = abs(atan((last_y - first_y) / (last_x - first_x)) * 180 / pi)

        if direction < diagonal_angle:
            step_profile = pix_width / cos(direction * pi / 180)
        else:
            step_profile = pix_height / sin(direction * pi / 180)

        dist = WorkerTerrain.distance2d((first_x, first_y), (last_x, last_y))
        vertices_count = ceil(dist / step_profile)
        profile_x = np.linspace(first_x, last_x, vertices_count, endpoint=True)
        profile_y = np.linspace(first_y, last_y, vertices_count, endpoint=True)

        if self.crs_vct != self.crs_rst:
            prf_x_rst, prf_y_rst = transf_coord(transf_vct_rst, profile_x, profile_y)
            pc_x_rst, pc_y_rst = transf_coord(transf_vct_rst, pc_coords[:, 0], pc_coords[:, 1])
        else:
            prf_x_rst, prf_y_rst = profile_x, profile_y
            pc_x_rst, pc_y_rst = pc_coords[:, 0], pc_coords[:, 1]

        prf_c, prf_r = crs2pixel(geotransf, prf_x_rst, prf_y_rst)
        pc_c, pc_r = crs2pixel(geotransf, pc_x_rst, pc_y_rst)

        profile_z = DTM_array[prf_r.astype(int), prf_c.astype(int)]
        pc_z = DTM_array[pc_r.astype(int), pc_c.astype(int)]

        profile_coords = np.column_stack((profile_x, profile_y, profile_z))
        profile_coords = list(map(list, profile_coords.reshape((-1, 3))))
        simplified_profile = simplify_profile(profile_coords, self.tolerance)
        
        return simplified_profile, pc_z

    def create_flight_profile_waypoints(self, pc_z, simplified_profile, strip_proj_centres, DTM_array, geotransf, waypoint_nr, pr):
        waypoints_coords = [w[:2] + [w[2] + self.altitude_AGL] for w in simplified_profile]

        strip_proj_centres = [f_pc + [pc_z[e]] for e, f_pc in enumerate(strip_proj_centres)]

        for i in range(len(waypoints_coords) - 1):
            start_w, end_w = waypoints_coords[i], waypoints_coords[i + 1]

            waypoint_x, waypoint_y, waypoint_ASL = float(start_w[0]), float(start_w[1]), float(start_w[-1])
            waypoint_AGL = round(self.altitude_AGL, 2)

            feat_waypnt = QgsFeature()
            feat_waypnt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(waypoint_x, waypoint_y)))
            feat_waypnt.setAttributes([waypoint_nr, round(waypoint_x, 2), round(waypoint_y, 2),
                                    round(waypoint_ASL, 2), waypoint_AGL])
            pr.addFeature(feat_waypnt)

            for proj_centre in strip_proj_centres:
                pc_x = proj_centre[-2].asPoint().x()
                pc_y = proj_centre[-2].asPoint().y()
                pc_z_ground = float(proj_centre[-1])
                if min(start_w[0], end_w[0]) <= pc_x <= max(start_w[0], end_w[0]) \
                        and min(start_w[1], end_w[1]) <= pc_y <= max(start_w[1], end_w[1]):
                    id = int(proj_centre[2])
                    new_ASL = float(z_at_3d_line((pc_x, pc_y), start_w, end_w))
                    new_AGL = new_ASL - pc_z_ground
                    self.layer.startEditing()
                    self.layer.changeAttributeValue(id, 4, round(new_ASL, 2))
                    self.layer.changeAttributeValue(id, 5, round(new_AGL, 2))
                    self.layer.commitChanges()
            waypoint_nr += 1

        # ostatni punkt
        end_w = waypoints_coords[-1]
        feat_waypnt = QgsFeature()
        feat_waypnt.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(end_w[0], end_w[1])))
        feat_waypnt.setAttributes([waypoint_nr, round(end_w[0], 2), round(end_w[1], 2),
                                round(end_w[-1], 2), round(self.altitude_AGL, 2)])
        pr.addFeature(feat_waypnt)
        return waypoint_nr + 1
    
    def finalize_layers(self, waypoints_layer, result):
        flight_line = create_flight_line(waypoints_layer, self.crs_vct)
        style_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'altitudes_utils', 'flight_line_style.qml'
        )
        flight_line.loadNamedStyle(style_path)

        self.layer.startEditing()
        self.layer.deleteAttributes([9, 10, 11])
        self.layer.commitChanges()

        self.layer_pol.startEditing()
        self.layer_pol.deleteAttributes([2, 3])
        self.layer_pol.commitChanges()

        change_layer_style(self.layer_pol, {'color': '200,200,200,30', 'color_border': '#000000', 'width_border': '0.2'})
        change_layer_style(self.layer, {'size': '1.0'})

        self.layer_pol.setName('photos')
        self.layer.setName('projection centres')

        waypoints_layer.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))
        flight_line.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))

        result.extend([self.layer, flight_line, waypoints_layer, self.layer_pol])


    def handle_cancel(self):
        """Handle pressed Cancel button"""
        self.progress.emit(0)
        self.enabled.emit(True)
        self.finished.emit(None, "flight_design")

    @staticmethod
    def distance2d(a, b):
        """Calculate distance between 2 points"""
        return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)