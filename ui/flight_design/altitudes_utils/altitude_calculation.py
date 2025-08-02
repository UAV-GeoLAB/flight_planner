def calculate_altitude(ui):
    """Calculate altitude ASL and AGL"""
    gsd = ui.doubleSpinBoxGSD.value() / 100
    max_h = ui.doubleSpinBoxMaxHeight.value()
    min_h = ui.doubleSpinBoxMinHeight.value()
    avg_terrain_height = (max_h + min_h) / 2

    if ui.radioButtonGSD.isChecked():
        altitude_AGL = gsd / ui.camera_handler.camera.sensor_size * ui.camera_handler.camera.focal_length
    elif ui.radioButtonAltAGL.isChecked():
        altitude_AGL = ui.doubleSpinBoxAltAGL.value()

    ui.progressBar.setValue(20)
    return avg_terrain_height + altitude_AGL, altitude_AGL