
from qgis.PyQt import QtWidgets
from .ui.camera_section import CameraSectionHandler
import os
from qgis.PyQt import uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flight_planner_v1_dialog_base.ui'))

class FlightPlannerPWDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.camera_handler = CameraSectionHandler(self)
        self.camera_handler.setup()