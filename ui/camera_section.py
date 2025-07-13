from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtCore import pyqtSlot
from ..camera.models import Camera
from ..camera.storage import delete_camera, load_cameras, add_new_camera
from ..utils import show_info

class CameraSectionHandler:
    def __init__(self, dialog):
        self.dialog = dialog
        self.cameras = []
        self.camera = None
        self.on_camera_changed = None

    def setup(self):
        self.reload_camera_list()
        self.dialog.comboBoxCamera.activated.connect(self.on_camera_selected)
        self.dialog.pushButtonSaveCamera.clicked.connect(lambda: self.on_save_camera())
        self.dialog.pushButtonDeleteCamera.clicked.connect(lambda: self.on_delete_camera())
        
        self.dialog.doubleSpinBoxFocalLength.valueChanged.connect(self._on_camera_params_changed)
        self.dialog.doubleSpinBoxSensorSize.valueChanged.connect(self._on_camera_params_changed)
        self.dialog.spinBoxPixelsAlongTrack.valueChanged.connect(self._on_camera_params_changed)
        self.dialog.spinBoxPixelsAcrossTrack.valueChanged.connect(self._on_camera_params_changed)
        
        self.dialog.comboBoxCamera.setCurrentIndex(0)
        self.on_camera_selected(0)

    def _on_camera_params_changed(self):
        if self.camera and self.camera.name == "Your camera":
            self.camera.focal_length = self.dialog.doubleSpinBoxFocalLength.value() / 1000
            self.camera.sensor_size = self.dialog.doubleSpinBoxSensorSize.value() / 1_000_000
            self.camera.pixels_along_track = self.dialog.spinBoxPixelsAlongTrack.value()
            self.camera.pixels_across_track = self.dialog.spinBoxPixelsAcrossTrack.value()

            if self.on_camera_changed:
                self.on_camera_changed()

    def reload_camera_list(self):
        self.cameras = sorted(load_cameras(), key=lambda c: c.name)
        cb = self.dialog.comboBoxCamera
        cb.clear()
        cb.addItems([cam.name for cam in self.cameras])
        cb.addItem("Your camera")

    def on_camera_selected(self, index):
        cb = self.dialog.comboBoxCamera
        name = cb.currentText()

        if name == "Your camera":
            self._enable_camera_fields(True)
            self.camera = Camera(
                name="Your camera",
                focal_length=self.dialog.doubleSpinBoxFocalLength.value() / 1000,
                sensor_size=self.dialog.doubleSpinBoxSensorSize.value() / 1_000_000,
                pixels_along_track=self.dialog.spinBoxPixelsAlongTrack.value(),
                pixels_across_track=self.dialog.spinBoxPixelsAcrossTrack.value()
            )
        else:
            camera = next((c for c in self.cameras if c.name == name), None)
            if camera:
                self.dialog.doubleSpinBoxFocalLength.setValue(camera.focal_length * 1000)
                self.dialog.doubleSpinBoxSensorSize.setValue(camera.sensor_size * 1_000_000)
                self.dialog.spinBoxPixelsAlongTrack.setValue(camera.pixels_along_track)
                self.dialog.spinBoxPixelsAcrossTrack.setValue(camera.pixels_across_track)
                self.camera = camera
            self._enable_camera_fields(False)

        self.dialog.pushButtonDeleteCamera.setEnabled(name != "Your camera")
        self.dialog.pushButtonSaveCamera.setEnabled(name == "Your camera")

        if self.on_camera_changed:
            self.on_camera_changed()

    @pyqtSlot()
    def on_save_camera(self):
        try:
            name, ok = QInputDialog.getText(self.dialog, "Save camera", "Enter camera name:")
            if not ok or not name:
                return

            new_camera = add_new_camera(
                name=name,
                focal_length=self.dialog.doubleSpinBoxFocalLength.value() / 1000,
                sensor_size=self.dialog.doubleSpinBoxSensorSize.value() / 1_000_000,
                pix_along=self.dialog.spinBoxPixelsAlongTrack.value(),
                pix_across=self.dialog.spinBoxPixelsAcrossTrack.value()
            )
            self.reload_camera_list()
            self.dialog.comboBoxCamera.setCurrentText(new_camera.name)
            self.on_camera_selected(self.dialog.comboBoxCamera.currentIndex())
        except Exception:
            show_info(title='Error', text='Saving camera failed', level='Critical')

    @pyqtSlot()
    def on_delete_camera(self):
        try:
            name = self.dialog.comboBoxCamera.currentText()
            cam = next((c for c in self.cameras if c.name == name), None)
            if not cam:
                show_info(title="Cannot delete", text="This camera is not deletable.", level="Information")
                return

            delete_camera(cam)
            self.cameras.remove(cam)

            self.reload_camera_list()
            if self.cameras:
                self.dialog.comboBoxCamera.setCurrentIndex(0)
                self.on_camera_selected(0)
            else:
                self.dialog.comboBoxCamera.clear()
                self.dialog.comboBoxCamera.addItem("Your camera")
                self.dialog.comboBoxCamera.setCurrentIndex(0)
                self.on_camera_selected(0)
        except Exception:
            show_info(title='Error', text='Deleting camera failed', level='Critical')

    def _enable_camera_fields(self, enable: bool):
        self.dialog.doubleSpinBoxFocalLength.setEnabled(enable)
        self.dialog.doubleSpinBoxSensorSize.setEnabled(enable)
        self.dialog.spinBoxPixelsAlongTrack.setEnabled(enable)
        self.dialog.spinBoxPixelsAcrossTrack.setEnabled(enable)
