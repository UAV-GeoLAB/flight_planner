from PyQt5.QtWidgets import QMessageBox
from ..utils import show_error

class AltitudeSectionHandler:
    def __init__(self, dialog, camera_handler):
        self.dialog = dialog
        self.camera_handler = camera_handler
        self.camera_handler.on_camera_changed = self._recalculate_values

    def setup(self):
        self.dialog.comboBoxAltitudeType.currentTextChanged.connect(self.on_altitude_type_changed)
        self.dialog.radioButtonAltAGL.toggled.connect(self.on_altitude_mode_toggled)
        
        self.dialog.doubleSpinBoxAltAGL.valueChanged.connect(self._on_altitude_changed)
        self.dialog.doubleSpinBoxGSD.valueChanged.connect(self._on_gsd_changed)

        self._on_mode_changed()
        self._recalculate_values()
    
    def _recalculate_values(self):
        if self.dialog.radioButtonGSD.isChecked():
            self._calculate_altitude()
        else:
            self._calculate_gsd()
    
    def _on_mode_changed(self):
        agl_mode = self.dialog.radioButtonAltAGL.isChecked()
        self.dialog.doubleSpinBoxAltAGL.setEnabled(agl_mode)
        self.dialog.doubleSpinBoxGSD.setEnabled(not agl_mode)
        self._recalculate_values()
    
    def _on_altitude_changed(self):
        """Handle altitude value change"""
        if self.dialog.radioButtonAltAGL.isChecked():
            self._calculate_gsd()

    def _on_gsd_changed(self):
        """Handle GSD value change"""
        if self.dialog.radioButtonGSD.isChecked():
            self._calculate_altitude()

    def _calculate_gsd(self):
        if not self.camera_handler.camera:
            return
            
        try:
            focal_mm = self.camera_handler.camera.focal_length * 1000
            sensor_mm = self.camera_handler.camera.sensor_size * 1000
            alt_m = self.dialog.doubleSpinBoxAltAGL.value()
            
            gsd_cm = (alt_m * 100 * sensor_mm) / (focal_mm * 10)
            self.dialog.doubleSpinBoxGSD.blockSignals(True)
            
            if gsd_cm > self.dialog.doubleSpinBoxGSD.maximum():
                self.dialog.doubleSpinBoxGSD.setSpecialValueText(f"> {self.dialog.doubleSpinBoxGSD.maximum()} [cm/px]")
                self.dialog.doubleSpinBoxGSD.setValue(self.dialog.doubleSpinBoxGSD.maximum())
            elif gsd_cm < self.dialog.doubleSpinBoxGSD.minimum():
                self.dialog.doubleSpinBoxGSD.setSpecialValueText(f"< {self.dialog.doubleSpinBoxGSD.minimum()} [cm/px]")
                self.dialog.doubleSpinBoxGSD.setValue(self.dialog.doubleSpinBoxGSD.minimum())
            else:
                self.dialog.doubleSpinBoxGSD.setSpecialValueText("")
                self.dialog.doubleSpinBoxGSD.setValue(gsd_cm)
                
            self.dialog.doubleSpinBoxGSD.blockSignals(False)
            
        except ZeroDivisionError:
            pass

    def _calculate_altitude(self):
        """Oblicza wysokość na podstawie GSD"""
        if not self.camera_handler.camera:
            return
            
        try:
            focal_m = self.camera_handler.camera.focal_length
            sensor_m = self.camera_handler.camera.sensor_size
            gsd_cm = self.dialog.doubleSpinBoxGSD.value()
            
            alt_m = (gsd_cm / 100 * focal_m) / sensor_m
            self.dialog.doubleSpinBoxAltAGL.blockSignals(True)
            
            if alt_m < self.dialog.doubleSpinBoxAltAGL.minimum():
                self.dialog.doubleSpinBoxAltAGL.setSpecialValueText(f"< {self.dialog.doubleSpinBoxAltAGL.minimum()} [m]")
                self.dialog.doubleSpinBoxAltAGL.setValue(self.dialog.doubleSpinBoxAltAGL.minimum())
            else:
                self.dialog.doubleSpinBoxAltAGL.setSpecialValueText("")
                self.dialog.doubleSpinBoxAltAGL.setValue(alt_m)
                
            self.dialog.doubleSpinBoxAltAGL.blockSignals(False)
            
        except ZeroDivisionError:
            pass


    def _reset_special_value(self, spin_box, min_or_max, unit, operator):
        text = spin_box.specialValueText()
        expected_text = f"{operator} {getattr(spin_box, min_or_max)()} [{unit}]"
        if text == expected_text:
            spin_box.setSpecialValueText("")
            spin_box.setValue(getattr(spin_box, min_or_max)())

    def on_altitude_mode_toggled(self):
        if self.dialog.radioButtonGSD.isChecked():
            self.dialog.doubleSpinBoxAltAGL.setEnabled(False)
            self.dialog.doubleSpinBoxGSD.setEnabled(True)
            self._reset_special_value(self.dialog.doubleSpinBoxGSD, "maximum", "cm/px", ">")
            self._reset_special_value(self.dialog.doubleSpinBoxGSD, "minimum", "cm/px", "<")
            self._calculate_altitude()
        elif self.dialog.radioButtonAltAGL.isChecked():
            self.dialog.doubleSpinBoxAltAGL.setEnabled(True)
            self.dialog.doubleSpinBoxGSD.setEnabled(False)
            self._reset_special_value(self.dialog.doubleSpinBoxAltAGL, "minimum", "m", "<")
            self._calculate_gsd()

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
