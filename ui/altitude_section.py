from PyQt5.QtWidgets import QMessageBox
from ..utils import show_error

class AltitudeSectionHandler:
    def __init__(self, dialog, camera_handler=None):
        self.dialog = dialog
        self.camera_handler = camera_handler

    def setup(self):
        self.dialog.comboBoxAltitudeType.currentTextChanged.connect(self.on_altitude_type_changed)
        self.dialog.radioButtonAltAGL.clicked.connect(self.on_altitude_mode_toggled)
        self.dialog.radioButtonGSD.clicked.connect(self.on_altitude_mode_toggled)

        self.dialog.doubleSpinBoxAltAGL.valueChanged.connect(self.update_altitude_or_gsd)
        self.dialog.doubleSpinBoxGSD.valueChanged.connect(self.update_altitude_or_gsd)
        self.dialog.doubleSpinBoxSensorSize.valueChanged.connect(self.on_sensor_size_changed)
        self.dialog.doubleSpinBoxFocalLength.valueChanged.connect(self.on_focal_length_changed)

        self._on_mode_changed()
    
    def _on_mode_changed(self):
        agl_mode = self.dialog.radioButtonAltAGL.isChecked()
        self.dialog.doubleSpinBoxAltAGL.setEnabled(agl_mode)
        self.dialog.doubleSpinBoxGSD.setEnabled(not agl_mode)

    def update_altitude_or_gsd(self):
        if self.dialog.radioButtonGSD.isChecked():
            self.check_set_altitude()
        elif self.dialog.radioButtonAltAGL.isChecked():
            self.check_set_gsd()
    
    def on_focal_length_changed(self):
        if not self.camera_handler or not self.camera_handler.camera:
            show_error("Camera is not defined")
            return
        self.camera_handler.camera.focal_length = self.dialog.doubleSpinBoxFocalLength.value() / 1_000
        self.update_altitude_or_gsd()

    def on_sensor_size_changed(self):
        if not self.camera_handler or not self.camera_handler.camera:
            show_error("Camera is not defined")
            return
        self.camera_handler.camera.sensor_size = self.dialog.doubleSpinBoxSensorSize.value() / 1_000_000
        self.update_altitude_or_gsd()

    def check_set_gsd(self):
        try:
            gsd = (self.dialog.doubleSpinBoxAltAGL.value()*100) \
                / (self.dialog.doubleSpinBoxFocalLength.value()/10) \
                * (self.dialog.doubleSpinBoxSensorSize.value()/10_000)
        except ZeroDivisionError:
            return

        if gsd > self.dialog.doubleSpinBoxGSD.maximum():
            self.dialog.doubleSpinBoxGSD.setSpecialValueText(f"> {self.dialog.doubleSpinBoxGSD.maximum()} [cm/px]")
        elif gsd < self.dialog.doubleSpinBoxGSD.minimum():
            self.dialog.doubleSpinBoxGSD.setSpecialValueText(f"< {self.dialog.doubleSpinBoxGSD.minimum()} [cm/px]")
        else:
            self.dialog.doubleSpinBoxGSD.setSpecialValueText("")
        self.dialog.doubleSpinBoxGSD.setValue(max(self.dialog.doubleSpinBoxGSD.minimum(), min(gsd, self.dialog.doubleSpinBoxGSD.maximum())))

    def check_set_altitude(self):
        try:
            alt = (self.dialog.doubleSpinBoxGSD.value()/100) \
                / (self.dialog.doubleSpinBoxSensorSize.value()/1_000_000) \
                * (self.dialog.doubleSpinBoxFocalLength.value()/1000)
        except ZeroDivisionError:
            return

        if alt < self.dialog.doubleSpinBoxAltAGL.minimum():
            self.dialog.doubleSpinBoxAltAGL.setSpecialValueText(f"< {self.dialog.doubleSpinBoxAltAGL.minimum()} [m]")
        else:
            self.dialog.doubleSpinBoxAltAGL.setSpecialValueText("")
        self.dialog.doubleSpinBoxAltAGL.setValue(max(self.dialog.doubleSpinBoxAltAGL.minimum(), alt))

    def _reset_special_value(self, spin_box, min_or_max, unit, operator):
        text = spin_box.specialValueText()
        expected_text = f"{operator} {getattr(spin_box, min_or_max)()} [{unit}]"
        if text == expected_text:
            spin_box.setSpecialValueText("")
            if operator == "<":
                spin_box.setValue(spin_box.minimum())
            else:
                spin_box.setValue(spin_box.maximum())

    def on_altitude_mode_toggled(self):
        if self.dialog.radioButtonGSD.isChecked():
            self.dialog.doubleSpinBoxAltAGL.setEnabled(False)
            self.dialog.doubleSpinBoxGSD.setEnabled(True)
            self._reset_special_value(self.dialog.doubleSpinBoxGSD, "maximum", "cm/px", ">")
            self._reset_special_value(self.dialog.doubleSpinBoxGSD, "minimum", "cm/px", "<")
            self.check_set_altitude()
        elif self.dialog.radioButtonAltAGL.isChecked():
            self.dialog.doubleSpinBoxAltAGL.setEnabled(True)
            self.dialog.doubleSpinBoxGSD.setEnabled(False)
            self._reset_special_value(self.dialog.doubleSpinBoxAltAGL, "minimum", "m", "<")
            self.check_set_gsd()

    def on_altitude_type_changed(self, text: str):
        if not isinstance(text, str):
            return

        if text in ['Separate Altitude ASL For Each Strip', 'Terrain Following'] \
           and not self.dialog.mMapLayerComboBoxDTM.currentLayer():
            QMessageBox.about(self.dialog, 'DTM needed', 'You must select DTM to use this option')
            self.dialog.comboBoxAltitudeType.setCurrentText("One Altitude ASL For Entire Flight")
            return

        self.dialog.doubleSpinBoxTolerance.setEnabled(text == 'Terrain Following')

        if text != 'One Altitude ASL For Entire Flight':
            self.dialog.checkBoxIncreaseOverlap.setChecked(False)
            self.dialog.checkBoxIncreaseOverlap.setEnabled(False)
            self.dialog.pushButtonGetHeights.setEnabled(False)
            self.dialog.doubleSpinBoxMaxHeight.setEnabled(False)
            self.dialog.doubleSpinBoxMinHeight.setEnabled(False)
        else:
            self.dialog.checkBoxIncreaseOverlap.setEnabled(True)
            self.dialog.pushButtonGetHeights.setEnabled(True)
            self.dialog.doubleSpinBoxMaxHeight.setEnabled(True)
            self.dialog.doubleSpinBoxMinHeight.setEnabled(True)

        is_terrain_following = (text == 'Terrain Following')
        self.dialog.radioButtonAltAGL.setEnabled(is_terrain_following)
        if not is_terrain_following:
            self.dialog.radioButtonGSD.setChecked(True)
