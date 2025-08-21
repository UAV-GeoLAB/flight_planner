from math import atan, pi, fabs, sqrt, atan2
from ....mathgeo_utils.algebra import bounding_box_at_angle
from ....mathgeo_utils.coordinates import line
from .projection_centres import strips_projection_centres_number, projection_centres
from ._annotation import annotate_segment_features
from ....error_reporting import QgsPrint, QgsMessBox
from qgis import processing
from qgis.core import QgsField, QgsCoordinateReferenceSystem
from PyQt5.QtCore import QMetaType

def process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL):
    """Get projection centres and photos layer from AoI"""
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
    """Get projection centres and photos layer from Corridor line"""
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
        pc_lay.addAttribute(QgsField("BuffNr", QMetaType.Int))

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


def corridor_flight_numbering(feats_exp_lines, buff_exp_lines, Bx, By,
    len_across, mult_base, x_percent, segments):
    """Return dictionary with number of strips and photos
    for each segment of corridor flight."""
    nr_photos_in_strip = {}
    for feat_exp in feats_exp_lines:
        x_start = feat_exp.geometry().asPolyline()[0].x()
        y_start = feat_exp.geometry().asPolyline()[0].y()
        x_end = feat_exp.geometry().asPolyline()[1].x()
        y_end = feat_exp.geometry().asPolyline()[1].y()
        a_line, b_line = line(y_start, y_end, x_start, x_end)
        angle = atan(a_line) * 180 / pi

        if angle < 0:
            angle = angle + 180
        if y_end - y_start < 0:
            angle = angle + 180

        featbuff_exp = buff_exp_lines.getFeature(feat_exp.id())
        geom_line_buf = featbuff_exp.geometry()
        a, b, a2, b2, Dx, Dy = bounding_box_at_angle(angle, geom_line_buf)
        Nx, Ny = strips_projection_centres_number(Dx, Dy, Bx, By,
            len_across, mult_base, x_percent)
        Nx = Nx - 2

        nr_photos_in_strip[f"segment_{feat_exp.id()}"] = Nx

    photo = 1
    strip = 1
    all_directions = []
    for direction in range(1, Ny+1):
        if direction % 2 != 0:
            last_strip, last_photo, strips_in_direction = forward(strip,
                photo, nr_photos_in_strip)
            strip = last_strip
            photo = last_photo
        else:
            last_strip, last_photo, strips_in_direction = backward(strip,
                photo, nr_photos_in_strip)
            strip = last_strip
            photo = last_photo
        all_directions.append(strips_in_direction)

    ordered_segments = {}
    for n in range(1, segments+1):
        segment_list = [d[f'segment_{n}'] for d in all_directions]
        segment_dict = {}
        for strip in segment_list:
            segment_dict.update(strip)
        ordered_segments[f'segment_{n}'] = segment_dict
        
    return ordered_segments

def forward(strip, photo, nr_photos_in_strip):
    """Return dictionary with strip and photo numbers
    for the forward direction of corridor flight."""
    strips_forward = {}
    for seg, n in nr_photos_in_strip.items():
        photos = []
        for _ in range(1, n + 1):
            photos.append(photo)
            photo += 1
        strips_forward[seg] = {strip: photos}
        strip += 1

    return strip, photo, strips_forward


def backward(strip, photo, nr_photos_in_strip):
    """Return dictionary with strip and photo numbers
    for the backward direction of corridor flight."""
    strips_backward = {}
    for seg, n in reversed(nr_photos_in_strip.items()):
        photos = []
        for _ in range(1, n + 1):
            photos.append(photo)
            photo += 1
        strips_backward[seg] = {strip: photos[::-1]}
        strip += 1

    return strip, photo, strips_backward