import os
import traceback
from math import (
    atan,
    ceil,
    cos,
    pi,
    sin
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

from ....functions import (
    change_layer_style,
    create_flight_line,
    crs2pixel,
    distance2d,
    simplify_profile,
    transf_coord,
    z_at_3d_line
)


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
        """Update altitude ASL and AGL for Following Terrain altitude type."""
        result = []
        try:
            geotransf = self.raster.GetGeoTransform()
            raster_array = self.raster.GetRasterBand(1).ReadAsArray()
            nodata = self.raster.GetRasterBand(1).GetNoDataValue()
            DTM_array = np.ma.masked_equal(raster_array, nodata)

            pix_width = geotransf[1]
            pix_height = -geotransf[5]
            if self.crs_rst != self.crs_vct:
                transf_vct_rst = Transformer.from_crs(self.crs_vct,
                                                    self.crs_rst,
                                                    always_xy=True)
                transf_rst_vct = Transformer.from_crs(self.crs_rst,
                                                    self.crs_vct,
                                                    always_xy=True)
                uplx = geotransf[0]
                uply = geotransf[3]
                uplx_n = uplx + pix_width
                uply_n = uply + pix_height
                xo, yo = transf_coord(transf_rst_vct, uplx, uply)
                xo1, yo1 = transf_coord(transf_rst_vct, uplx_n, uply_n)
                pix_width = distance2d((xo, yo), (xo1, yo))
                pix_height = distance2d((xo, yo), (xo, yo1))
            raster_diagonal_angle = atan(pix_height/pix_width)*180/pi

            waypoints_layer = QgsVectorLayer("Point?crs=" + str(self.crs_vct),
                                    "waypoints", "memory")
            pr = waypoints_layer.dataProvider()
            pr.addAttributes([QgsField("Waypoint Number", QVariant.Int),
                            QgsField("X [m]", QVariant.Double),
                            QgsField("Y [m]", QVariant.Double),
                            QgsField("Alt. ASL [m]", QVariant.Double),
                            QgsField("Alt. AGL [m]", QVariant.Double)])
            waypoints_layer.updateFields()

            strips_nr = int(self.layer.maximumValue(0))
            feats = self.layer.getFeatures()
            proj_cent_list = [f.attributes()[:2] + [f.id(), f.geometry()] for f in feats]
            proj_cent_list.sort(key=lambda x: x[1])

            progress_c = 0
            step = int(self.layer.maximumValue(0)) // 1000
            waypoint_nr = 1
            for strip_nr in range(1, strips_nr+1):
                if self.killed is True:
                    self.handle_cancel()
                    break
                QApplication.processEvents()

                strip_proj_centres = [f for f in proj_cent_list if int(f[0]) == strip_nr]
                pc_coords = [(p[-1].asPoint().x(), p[-1].asPoint().y()) for p in strip_proj_centres]
                pc_coords = np.array(pc_coords)
                first_pc = strip_proj_centres[0]
                last_pc = strip_proj_centres[-1]

                first_x = first_pc[-1].asPoint().x()
                first_y = first_pc[-1].asPoint().y()
                last_x = last_pc[-1].asPoint().x()
                last_y = last_pc[-1].asPoint().y()

                direction = 90
                if last_x-first_x != 0:
                    direction = abs(atan((last_y-first_y) / (last_x-first_x))*180/pi)

                if direction < raster_diagonal_angle:
                    step_profile = pix_width / cos(direction*pi/180)
                else:
                    step_profile = pix_height / sin(direction*pi/180)

                vertices_count = ceil(distance2d((first_x, first_y), (last_x, last_y))/step_profile)
                profile_x = np.linspace(first_x, last_x, vertices_count, endpoint=True)
                profile_y = np.linspace(first_y, last_y, vertices_count, endpoint=True)

                if self.crs_vct != self.crs_rst:
                    prf_x_rst, prf_y_rst = transf_coord(transf_vct_rst, profile_x, profile_y)
                    prf_c, prf_r = crs2pixel(geotransf, prf_x_rst, prf_y_rst)
                    pc_x_rst, pc_y_rst = transf_coord(transf_vct_rst, pc_coords[:, 0], pc_coords[:, 1])
                    pc_c, pc_r = crs2pixel(geotransf, pc_x_rst, pc_y_rst)
                else:
                    prf_c, prf_r = crs2pixel(geotransf, profile_x, profile_y)
                    pc_c, pc_r = crs2pixel(geotransf, pc_coords[:, 0], pc_coords[:, 1])

                profile_z = DTM_array[prf_r.astype(int), prf_c.astype(int)]
                pc_z = DTM_array[pc_r.astype(int), pc_c.astype(int)]

                profile_coords = np.column_stack((profile_x, profile_y, profile_z))
                profile_coords = list(map(list, profile_coords.reshape((-1, 3))))
                simplified_profile = simplify_profile(profile_coords, self.tolerance)
                waypoints_coords = [w[:2] + [w[2] + self.altitude_AGL] for w in simplified_profile]

                strip_proj_centres = [f_pc + [pc_z[e]] for e, f_pc in enumerate(strip_proj_centres)]
                for i in range(len(waypoints_coords[:-1])):
                    start_w = waypoints_coords[i]
                    end_w = waypoints_coords[i+1]

                    waypoint_x = float(start_w[0])
                    waypoint_y = float(start_w[1])
                    waypoint_ASL = float(start_w[-1])
                    waypoint_AGL = round(self.altitude_AGL,2)

                    feat_waypnt = QgsFeature()
                    waypnt = QgsPointXY(waypoint_x, waypoint_y)
                    feat_waypnt.setGeometry(QgsGeometry.fromPointXY(waypnt))
                    feat_waypnt.setAttributes([waypoint_nr, round(waypoint_x,2),
                        round(waypoint_y,2), round(waypoint_ASL,2), waypoint_AGL])
                    pr.addFeature(feat_waypnt)

                    for proj_centre in strip_proj_centres:
                        pc_x = proj_centre[-2].asPoint().x()
                        pc_y = proj_centre[-2].asPoint().y()
                        pc_z_ground = float(proj_centre[-1])

                        if min(start_w[0], end_w[0]) <= pc_x <= max(start_w[0], end_w[0]) \
                        and min(start_w[1], end_w[1]) <= pc_y <= max(start_w[1], end_w[1]):
                            id = int(proj_centre[2])
                            new_ASL =  float(z_at_3d_line((pc_x, pc_y), start_w, end_w))
                            new_AGL = new_ASL - pc_z_ground
                            self.layer.startEditing()
                            self.layer.changeAttributeValue(id, 4, round(new_ASL, 2))
                            self.layer.changeAttributeValue(id, 5, round(new_AGL, 2))
                            self.layer.commitChanges()
                    waypoint_nr += 1

                waypoint_x = float(end_w[0])
                waypoint_y = float(end_w[1])
                waypoint_ASL = float(end_w[-1])

                feat_waypnt = QgsFeature()
                waypnt = QgsPointXY(waypoint_x, waypoint_y)
                feat_waypnt.setGeometry(QgsGeometry.fromPointXY(waypnt))
                feat_waypnt.setAttributes([waypoint_nr, round(waypoint_x,2),
                        round(waypoint_y,2), round(waypoint_ASL,2), waypoint_AGL])
                pr.addFeature(feat_waypnt)
                waypoints_layer.updateExtents()
                waypoint_nr += 1

                # increment progress
                progress_c += 1
                if step == 0 or progress_c % step == 0:
                    progress_range = 100 - self.start_progress
                    progress_value = self.start_progress + int((progress_c / strips_nr) * progress_range)
                    self.progress.emit(progress_value)
            if self.killed is False:
                self.progress.emit(100)
                flight_line = create_flight_line(waypoints_layer, self.crs_vct)
                style_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'altitudes_utils',
                    'flight_line_style.qml'
                )
                flight_line.loadNamedStyle(style_path)
                # deleting reduntant fields
                self.layer.startEditing()
                self.layer.deleteAttributes([9, 10, 11])
                self.layer.commitChanges()
                self.layer_pol.startEditing()
                self.layer_pol.deleteAttributes([2, 3])
                self.layer_pol.commitChanges()
                # changing layer style
                prop = {'color': '200,200,200,30', 'color_border': '#000000',
                        'width_border': '0.2'}
                change_layer_style(self.layer_pol, prop)
                change_layer_style(self.layer, {'size': '1.0'})
                self.layer_pol.setName('photos')
                self.layer.setName('projection centres')
                waypoints_layer.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))
                flight_line.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))
                result.append(self.layer)
                result.append(flight_line)
                result.append(waypoints_layer)
                result.append(self.layer_pol)
        except Exception as e:
            # forward the exception upstream
            self.error.emit(e, traceback.format_exc())
            self.progress.emit(0)
            self.enabled.emit(True)

        self.finished.emit(result, "flight_design")
        self.enabled.emit(True)

    def handle_cancel(self):
        """Handle pressed Cancel button"""
        self.progress.emit(0)
        self.enabled.emit(True)
        self.finished.emit(None, "flight_design")