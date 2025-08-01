import os
from ....functions import create_waypoints, create_flight_line, change_layer_style, add_to_canvas
from qgis.core import QgsCoordinateReferenceSystem

def prepare_and_style_layers(ui, pc_lay, photo_lay):
    waypoints_layer = create_waypoints(pc_lay, ui.crs_vct)
    waypoints_layer.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code)) # Transform

    flight_line = create_flight_line(waypoints_layer, ui.crs_vct)
    flight_line.setCrs(QgsCoordinateReferenceSystem(ui.epsg_code)) # Transform
    
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flight_line_style.qml')
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

    add_to_canvas([pc_lay, flight_line, waypoints_layer, photo_lay], "flight_design", ui.design_run_counter)
    ui.design_run_counter += 1
    ui.progressBar.setValue(100)