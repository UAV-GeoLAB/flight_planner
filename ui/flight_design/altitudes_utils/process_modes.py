from math import atan, pi, fabs, sqrt, atan2
from qgis import processing
from ....functions import bounding_box_at_angle, projection_centres, corridor_flight_numbering, line
from ._annotation import annotate_segment_features
from ....error_reporting import QgsPrint, QgsMessBox
from qgis.core import QgsField, QgsCoordinateReferenceSystem
from PyQt5.QtCore import QVariant


def process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL):
    if ui.AreaOfInterest and ui.AreaOfInterest.crs().isValid():
        ui.crs_vct = ui.AreaOfInterest.crs()
    else:
        ui.crs_rst = QgsCoordinateReferenceSystem(ui.epsg_code)
        QgsMessBox('AoI CRS Error', f'Your AoI has no valid CRS.\n{ui.epsg_code} set.')
    
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
    pc_lay.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code))
    photo_lay.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code))
    theta = fabs(atan2(len_across / 2, len_along / 2))
    dist = sqrt((len_along / 2) ** 2 + (len_across / 2) ** 2)
    return pc_lay, photo_lay, theta, dist

def process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL):
    if ui.CorLine and ui.CorLine.crs().isValid():
        ui.crs_vct = ui.CorLine.crs()
    else:
        ui.crs_rst = QgsCoordinateReferenceSystem(ui.epsg_code)
        QgsMessBox('Corridor line CRS Error', f'Your Corridor line has no valid CRS.\n{ui.epsg_code} set.')

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
    pc_lay_list, photo_lay_list, line_buf_list = [], [], []
    segments = len([f for f in exploded_lines.getFeatures()])
    
    ordered_segments = corridor_flight_numbering(
        exploded_lines.getFeatures(), buffered_exp_lines,
        Bx, By, len_across, ui.spinBoxMultipleBase.value(), ui.spinBoxExceedExtremeStrips.value(), segments
    )

    segment_nr = 1
    strip = 0
    photo = 0
    for feat_exp in feats_exp_lines:
        coords = feat_exp.geometry().asPolyline()
        try:
            x_start, y_start = coords[0].x(), coords[0].y()
            x_end, y_end = coords[1].x(), coords[1].y()
        except IndexError as e:
            QgsPrint(f"Index error: {e} - coords: {coords}")
            continue

        a_line, _ = line(y_start, y_end, x_start, x_end)
        angle = atan(a_line) * 180 / pi
        if angle < 0:
            angle += 180
        if y_end - y_start < 0:
            angle += 180

        featbuff_exp = buffered_exp_lines.getFeature(segment_nr)
        geom_line_buf = featbuff_exp.geometry()
        line_buf_list.append(geom_line_buf)
        a, b, a2, b2, Dx, Dy = bounding_box_at_angle(angle, geom_line_buf)

        pc_lay, photo_lay, s_nr, p_nr = projection_centres(
            angle, geom_line_buf, ui.crs_vct, a, b, a2, b2, Dx, Dy,
            Bx, By, len_along, len_across, ui.spinBoxExceedExtremeStrips.value(), ui.spinBoxMultipleBase.value(),
            altitude_ASL, strip, photo
        )
        pc_lay.startEditing()
        photo_lay.startEditing()
        pc_lay.addAttribute(QgsField("BuffNr", QVariant.Int))

        annotate_segment_features(pc_lay, photo_lay, ordered_segments[f'segment_{segment_nr}'], segment_nr)
        pc_lay_list.append(pc_lay)
        photo_lay_list.append(photo_lay)
        strip = s_nr
        photo = p_nr
        segment_nr += 1

    pc_lay = processing.run("native:mergevectorlayers",
                            {'LAYERS': pc_lay_list,
                             'CRS': None, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    photo_lay = processing.run("native:mergevectorlayers",
                               {'LAYERS': photo_lay_list,
                                'CRS': None, 'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
    pc_lay.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code))
    photo_lay.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code))
    theta = fabs(atan2(len_across / 2, len_along / 2))
    dist = sqrt((len_along / 2) ** 2 + (len_across / 2) ** 2)
    return pc_lay, photo_lay, line_buf_list, theta, dist