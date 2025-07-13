from qgis.PyQt import QtWidgets
from .ui.camera_section import CameraSectionHandler
from .ui.altitude_section import AltitudeSectionHandler
from .ui.terrain_section import TerrainSectionHandler
from .ui.direction_section import DirectionSectionHandler
import os
from .utils import show_error
from qgis.PyQt import uic
from osgeo import gdal
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

        self.terrain_handler = TerrainSectionHandler(self)
        self.pushButtonGetHeights.clicked.connect(lambda _: self.terrain_handler.on_btn_get_heights_clicked())

        self.direction_handler = DirectionSectionHandler(self.dial, self.spinBoxDirection)
        
        self.comboBoxAltitudeType.addItems(["One Altitude ASL For Entire Flight",
            "Separate Altitude ASL For Each Strip",
            "Terrain Following"])
        
        self.mMapLayerComboBoxProjectionCentres.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mFieldComboBoxAltControl.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxOmega.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxPhi.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxKappa.setFilters(QgsFieldProxyModel.Numeric)
        self.mMapLayerComboBoxDTM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBoxAoI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.mMapLayerComboBoxCorridor.setFilters(QgsMapLayerProxyModel.LineLayer)

        self._init_default_layers()
    
    def _init_default_layers(self):
        self.on_mMapLayerComboBoxDTM_layerChanged()
        self.on_mMapLayerComboBoxAoI_layerChanged()
        self.on_mMapLayerComboBoxCorridor_layerChanged()
    
    def on_mMapLayerComboBoxDTM_layerChanged(self):
        lyr = self.mMapLayerComboBoxDTM.currentLayer()
        self.DTM = lyr
        if lyr:
            try:
                self.raster = gdal.Open(lyr.source())
                self.terrain_handler.set_dtm(lyr, self.raster)
            except Exception as e:
                show_error("Error loading DTM: {e}", "Critical")

    def on_mMapLayerComboBoxAoI_layerChanged(self):
        lyr = self.mMapLayerComboBoxAoI.currentLayer()
        self.AreaOfInterest = lyr
        if lyr:
            self.terrain_handler.set_aoi(lyr)

    def on_mMapLayerComboBoxCorridor_layerChanged(self):
        lyr = self.mMapLayerComboBoxCorridor.currentLayer()
        self.pathLine = lyr
        if lyr:
            self.terrain_handler.set_corridor_line(lyr)
