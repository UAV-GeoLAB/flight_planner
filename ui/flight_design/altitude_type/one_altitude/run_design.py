from .....utils import show_error
from .....functions import *
from pyproj import Transformer
import os

def run_design_one_altitude(ui):
    try:
        ui.pushButtonRunDesign.setEnabled(False)
        ui.progressBar.setValue(0)
        ui.progressBar.setFormat("%p%")
        ui.progressBar.setRange(0, 100)

        gsd = ui.doubleSpinBoxGSD.value() / 100
        max_h = ui.doubleSpinBoxMaxHeight.value()
        min_h = ui.doubleSpinBoxMinHeight.value()
        p0 = ui.doubleSpinBoxOverlap.value()
        q0 = ui.doubleSpinBoxSidelap.value()
        mult_base = ui.spinBoxMultipleBase.value()
        x_percent = ui.spinBoxExceedExtremeStrips.value()
        ui.progressBar.setValue(5)

        if not hasattr(ui.camera_handler, 'camera') or ui.camera_handler.camera is None:
            show_error("Camera is not configured properly.", level="Critical")
            return
        camera = ui.camera_handler.camera
        ui.progressBar.setValue(10)

        avg_terrain_height = (max_h + min_h) / 2
        if ui.radioButtonGSD.isChecked():
            altitude_AGL = gsd / camera.sensor_size * camera.focal_length
        elif ui.radioButtonAltAGL.isChecked():
            altitude_AGL = ui.doubleSpinBoxAltAGL.value()
        altitude_ASL = avg_terrain_height + altitude_AGL
        ui.progressBar.setValue(20)

        if not ui.checkBoxIncreaseOverlap.isChecked():
            ui.p = p0 / 100
            ui.q = q0 / 100

        len_along = camera.pixels_along_track * gsd
        len_across = camera.pixels_across_track * gsd
        Bx = len_along * (1 - ui.p)
        By = len_across * (1 - ui.q)
        strip = 0
        photo = 0
        ui.progressBar.setValue(30)

        ui.geom_AoI = ui.get_geom_AoI()
        if ui.geom_AoI is None:
            return
        ui.progressBar.setValue(35)
        
        layer = ui.mMapLayerComboBoxAoI.currentLayer()
        if layer:
            ui.crs_vct = layer.crs()
        else:
            raise ValueError("AoI has no valid CRS.")

        if ui.DTM and ui.DTM.crs().isValid():
            ui.crs_rst = ui.DTM.crs() 
        else:
            raise ValueError("DTM has no valid CRS.")
        ui.progressBar.setValue(40)

        if ui.tabBlock:
            angle = 90 - ui.spinBoxDirection.value()
            if angle < 0:
                angle += 360
            a, b, a2, b2, Dx, Dy = bounding_box_at_angle(angle, ui.geom_AoI)

            pc_lay, photo_lay, s_nr, p_nr = projection_centres(
                angle, ui.geom_AoI, ui.crs_vct, a, b, a2, b2, Dx, Dy,
                Bx, By, len_along, len_across, x_percent, mult_base,
                altitude_ASL, strip, photo
            )
            pc_lay.setCrs(ui.crs_vct)
            photo_lay.setCrs(ui.crs_vct)
        ui.progressBar.setValue(55)

        if hasattr(ui, 'DTM'):
            if ui.crs_rst != ui.crs_vct:
                transf_vct_rst = Transformer.from_crs(ui.crs_vct.authid(), ui.crs_rst.authid(), always_xy=True)

            feats = pc_lay.getFeatures()
            pc_lay.startEditing()
            for f in feats:
                x = f.geometry().asPoint().x()
                y = f.geometry().asPoint().y()
                if ui.crs_rst != ui.crs_vct:
                    x, y = transf_vct_rst.transform(x, y)

                altitude_ASL_f = f.attribute('Alt. ASL [m]')
                terrain_height, res = ui.DTM.dataProvider().sample(QgsPointXY(x, y), 1)
                altitude_AGL_f = altitude_ASL_f - terrain_height
                pc_lay.changeAttributeValue(f.id(), 5, round(altitude_AGL_f, 2))
            pc_lay.commitChanges()
        ui.progressBar.setValue(70)

        waypoints_layer = create_waypoints(pc_lay, ui.crs_vct)
        flight_line = create_flight_line(waypoints_layer, ui.crs_vct)
        waypoints_layer.setCrs(ui.crs_vct)
        flight_line.setCrs(ui.crs_vct)
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
        ui.progressBar.setValue(90)

        photo_lay.setName('photos')
        pc_lay.setName('projection centres')

        layers = [pc_lay, flight_line, waypoints_layer, photo_lay]
        add_layers_to_canvas(layers, "flight_design", ui.design_run_counter)
        ui.design_run_counter += 1
        ui.progressBar.setValue(100)

    except Exception as e:
        ui.progressBar.setValue(0)
        show_error(f"Error: {str(e)}", level="Critical")
    finally:
        ui.pushButtonRunDesign.setEnabled(True)