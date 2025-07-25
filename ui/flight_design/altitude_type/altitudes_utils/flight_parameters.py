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