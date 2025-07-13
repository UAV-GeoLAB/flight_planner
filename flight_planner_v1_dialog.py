from qgis.PyQt import QtWidgets
from .ui.camera_section import CameraSectionHandler
from .ui.altitude_section import AltitudeSectionHandler
from .ui.direction_section import DirectionSectionHandler
import os
from qgis.PyQt import uic
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flight_planner_v1_dialog_base.ui'))

class FlightPlannerPWDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.camera_handler = CameraSectionHandler(self)
        self.camera_handler.setup()

        self.altitude_handler = AltitudeSectionHandler(self, self.camera_handler)
        self.altitude_handler.setup()

        self.direction_handler = DirectionSectionHandler(self.dial, self.spinBoxDirection)
        
        self.comboBoxAltitudeType.addItems(["One Altitude ASL For Entire Flight",
            "Separate Altitude ASL For Each Strip",
            "Terrain Following"])
        
        # Filters for ComboBoxes data types
        self.mMapLayerComboBoxProjectionCentres.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mFieldComboBoxAltControl.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxOmega.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxPhi.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxKappa.setFilters(QgsFieldProxyModel.Numeric)
        self.mMapLayerComboBoxDTM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBoxAoI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.mMapLayerComboBoxCorridor.setFilters(QgsMapLayerProxyModel.LineLayer)
