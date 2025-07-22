from .....utils import show_error, show_info, traceback_error
from .....functions import *
from pyproj import Transformer
import processing
import os
from qgis.core import QgsCoordinateReferenceSystem, QgsPointXY
from math import atan, pi

def run_design_one_altitude(ui):
    ui.pushButtonRunDesign.setEnabled(False)
    try:
        if not validate_inputs(ui):
            return

        initialize_crs_and_progressbar(ui)

        altitude_ASL = calculate_altitude(ui)
        Bx, By, len_along, len_across = calculate_flight_parameters(ui)

        if ui.tabBlock:
            pc_lay, photo_lay = process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL)
        elif ui.tabCorridor:
            pc_lay, photo_lay = process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL)

        enrich_projection_centres_with_agl(ui, pc_lay)
        prepare_and_style_layers(ui, pc_lay, photo_lay)

    except Exception:
        ui.progressBar.setValue(0)
        traceback_error()
    finally:
        ui.pushButtonRunDesign.setEnabled(True)

def validate_inputs(ui):
    if not hasattr(ui.camera_handler, 'camera') or ui.camera_handler.camera is None:
        show_error("Camera is not configured properly.", level="Critical")
        return False

    if ui.tabBlock and (not hasattr(ui, 'AreaOfInterest') or ui.AreaOfInterest is None):
        show_info('AoI needed', 'You have to load Area of Interest layer')
        return False
    elif ui.tabCorridor and (not hasattr(ui, "pathLine") or ui.pathLine is None):
        show_info('Corridor line needed', 'You have to load Corridor line layer')
        return False

    return True

def initialize_crs_and_progressbar(ui):
    if ui.DTM and ui.DTM.crs().isValid():
        ui.crs_rst = ui.DTM.crs()
    else:
        ui.crs_rst = QgsCoordinateReferenceSystem(ui.epsg_code)
        show_info('DTM CRS', f'Your DTM did not have CRS. {ui.epsg_code} set.')

    ui.pushButtonRunDesign.setEnabled(False)
    ui.progressBar.setValue(0)
    ui.progressBar.setFormat("%p%")
    ui.progressBar.setRange(0, 100)

def calculate_altitude(ui):
    gsd = ui.doubleSpinBoxGSD.value() / 100
    max_h = ui.doubleSpinBoxMaxHeight.value()
    min_h = ui.doubleSpinBoxMinHeight.value()
    avg_terrain_height = (max_h + min_h) / 2

    if ui.radioButtonGSD.isChecked():
        altitude_AGL = gsd / ui.camera_handler.camera.sensor_size * ui.camera_handler.camera.focal_length
    elif ui.radioButtonAltAGL.isChecked():
        altitude_AGL = ui.doubleSpinBoxAltAGL.value()

    ui.progressBar.setValue(20)
    return avg_terrain_height + altitude_AGL

def calculate_flight_parameters(ui):
    gsd = ui.doubleSpinBoxGSD.value() / 100
    camera = ui.camera_handler.camera

    if not ui.checkBoxIncreaseOverlap.isChecked():
        ui.p = ui.doubleSpinBoxOverlap.value() / 100
        ui.q = ui.doubleSpinBoxSidelap.value() / 100

    len_along = camera.pixels_along_track * gsd
    len_across = camera.pixels_across_track * gsd
    Bx = len_along * (1 - ui.p)
    By = len_across * (1 - ui.q)

    ui.progressBar.setValue(30)
    return Bx, By, len_along, len_across

def process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL):
    if not ui.AreaOfInterest.crs().isValid():
        raise ValueError("AoI has no valid CRS.")

    ui.crs_vct = ui.AreaOfInterest.crs()
    feature = list(ui.AreaOfInterest.getFeatures())[0]
    ui.aoi_geom = feature.geometry()

    angle = 90 - ui.spinBoxDirection.value()
    if angle < 0:
        angle += 360
    a, b, a2, b2, Dx, Dy = bounding_box_at_angle(angle, ui.aoi_geom)

    pc_lay, photo_lay, _, _ = projection_centres(
        angle, ui.aoi_geom, ui.crs_vct, a, b, a2, b2, Dx, Dy,
        Bx, By, len_along, len_across,
        ui.spinBoxExceedExtremeStrips.value(),
        ui.spinBoxMultipleBase.value(), altitude_ASL, 0, 0
    )
    pc_lay.setCrs(ui.crs_vct)
    photo_lay.setCrs(ui.crs_vct)
    return pc_lay, photo_lay

def process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL):
    if not ui.CorLine.crs().isValid():
        raise ValueError("Corridor line has no valid CRS.")

    ui.crs_vct = ui.CorLine.crs()
    exploded_lines = processing.run("native:explodelines", {
        'INPUT': ui.pathLine,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    buffered_exp_lines = processing.run("native:buffer", {
        'INPUT': exploded_lines,
        'DISTANCE': ui.doubleSpinBoxBuffer.value(),
        'SEGMENTS': 5,
        'END_CAP_STYLE': 1,
        'JOIN_STYLE': 1,
        'MITER_LIMIT': 2,
        'DISSOLVE': False,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    feats_exp_lines = exploded_lines.getFeatures()
    pc_lay_list, photo_lay_list = [], []
    ordered_segments = corridor_flight_numbering(
        feats_exp_lines, buffered_exp_lines,
        Bx, By, len_across,
        ui.spinBoxMultipleBase.value(),
        ui.spinBoxExceedExtremeStrips.value(),
        len([f for f in exploded_lines.getFeatures()])
    )

    segment_nr = 1
    strip = 0
    photo = 0
    for feat_exp in feats_exp_lines:
        try:
            coords = feat_exp.geometry().asPolyline()
            x_start, y_start = coords[0].x(), coords[0].y()
            x_end, y_end = coords[1].x(), coords[1].y()
        except IndexError:
            continue

        a_line, _ = line(y_start, y_end, x_start, x_end)
        angle = atan(a_line) * 180 / pi
        if angle < 0:
            angle += 180
        if y_end - y_start < 0:
            angle += 180

        geom_line_buf = buffered_exp_lines.getFeature(segment_nr).geometry()
        a, b, a2, b2, Dx, Dy = bounding_box_at_angle(angle, geom_line_buf)
        pc_lay, photo_lay, s_nr, p_nr = projection_centres(
            angle, geom_line_buf, ui.crs_vct, a, b, a2, b2, Dx, Dy,
            Bx, By, len_along, len_across,
            ui.spinBoxExceedExtremeStrips.value(),
            ui.spinBoxMultipleBase.value(), altitude_ASL, strip, photo
        )

        annotate_segment_features(pc_lay, photo_lay, ordered_segments[f'segment_{segment_nr}'], segment_nr)
        pc_lay_list.append(pc_lay)
        photo_lay_list.append(photo_lay)
        strip = s_nr
        photo = p_nr
        segment_nr += 1

    pc_lay = processing.run("native:mergevectorlayers", {'LAYERS': pc_lay_list, 'CRS': None, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    photo_lay = processing.run("native:mergevectorlayers", {'LAYERS': photo_lay_list, 'CRS': None, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    pc_lay.setCrs(ui.crs_vct)
    photo_lay.setCrs(ui.crs_vct)
    return pc_lay, photo_lay

def annotate_segment_features(pc_lay, photo_lay, segment, segment_nr):
    pc_lay.startEditing()
    photo_lay.startEditing()
    feature_id = 1
    for strip_nr, photos_nr in segment.items():
        for photo_nr in photos_nr:
            st_nr = '%04d' % strip_nr
            ph_nr = '%05d' % photo_nr
            pc_lay.changeAttributeValue(feature_id, 0, st_nr)
            pc_lay.changeAttributeValue(feature_id, 1, ph_nr)
            pc_lay.changeAttributeValue(feature_id, 9, segment_nr)
            photo_lay.changeAttributeValue(feature_id, 0, st_nr)
            photo_lay.changeAttributeValue(feature_id, 1, ph_nr)
            feature_id += 1
    pc_lay.commitChanges()
    photo_lay.commitChanges()

def enrich_projection_centres_with_agl(ui, pc_lay):
    if not hasattr(ui, 'DTM'):
        return

    if ui.crs_rst != ui.crs_vct:
        transf_vct_rst = Transformer.from_crs(ui.crs_vct.authid(), ui.crs_rst.authid(), always_xy=True)

    feats = pc_lay.getFeatures()
    pc_lay.startEditing()
    for f in feats:
        x, y = f.geometry().asPoint().x(), f.geometry().asPoint().y()
        if ui.crs_rst != ui.crs_vct:
            x, y = transf_vct_rst.transform(x, y)

        altitude_ASL_f = f.attribute('Alt. ASL [m]')
        terrain_height, _ = ui.DTM.dataProvider().sample(QgsPointXY(x, y), 1)
        altitude_AGL_f = altitude_ASL_f - terrain_height
        pc_lay.changeAttributeValue(f.id(), 5, round(altitude_AGL_f, 2))
    pc_lay.commitChanges()
    ui.progressBar.setValue(70)

def prepare_and_style_layers(ui, pc_lay, photo_lay):
    waypoints_layer = create_waypoints(pc_lay, ui.crs_vct)
    flight_line = create_flight_line(waypoints_layer, ui.crs_vct)
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'flight_line_style.qml')
    flight_line.loadNamedStyle(style_path)

    pc_lay.startEditing()
    pc_lay.deleteAttributes([9, 10, 11])
    pc_lay.commitChanges()
    photo_lay.startEditing()
    photo_lay.deleteAttributes([2, 3])
    photo_lay.commitChanges()
    ui.progressBar.setValue(80)

    change_layer_style(photo_lay, {'color': '200,200,200,30', 'color_border': '#000000', 'width_border': '0.2'})
    change_layer_style(pc_lay, {'size': '1.0'})

    photo_lay.setName('photos')
    pc_lay.setName('projection centres')

    add_layers_to_canvas([pc_lay, flight_line, waypoints_layer, photo_lay], "flight_design", ui.design_run_counter)
    ui.design_run_counter += 1
    ui.progressBar.setValue(100)
