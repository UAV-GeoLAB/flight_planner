import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flight_planner_v1_dialog_base.ui'))


class FlightPlannerPWDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(FlightPlannerPWDialog, self).__init__(parent)
        self.setupUi(self)
