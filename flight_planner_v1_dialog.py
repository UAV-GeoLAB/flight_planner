from qgis.PyQt import QtWidgets
from .ui.camera_section import CameraSectionHandler
from .ui.altitude_section import AltitudeSectionHandler
from .ui.terrain_section import TerrainSectionHandler
from .ui.direction_section import DirectionSectionHandler
import os
from .utils import show_error
from qgis.PyQt import uic
from osgeo import gdal
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel, QgsCoordinateReferenceSystem
from .ui.flight_design.altitude_type.one_altitude.run_design import run_design_one_altitude
from .ui.flight_design.altitude_type.separate_altitude.run_design import run_design_separate_altitude
from .ui.flight_design.altitude_type.terrain_following.run_design import run_design_terrain_following
from PyQt5.QtCore import QThread
from .ui.flight_design.altitude_type.separate_altitude.worker import Worker
from PyQt5 import QtWidgets
from qgis.core import QgsProject, QgsMessageLog, Qgis
from .functions import add_layers_to_canvas


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flight_planner_v1_dialog_base.ui'))

class FlightPlannerPWDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.pushButtonCancelDesign.setVisible(False)

        self.tabBlock = True
        self.tabCorridor = False
        self.tabWidgetBlockCorridor.currentChanged.connect(self.on_tabWidgetBlockCorridor_currentChanged)

        self.epsg_code = None

        self.design_run_counter = 1
        
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

        # Disconnect previous connections to avoid multiple calls
        try:
            self.pushButtonRunDesign.clicked.disconnect()
        except TypeError:
            pass
        self.pushButtonRunDesign.clicked.connect(self.on_pushButtonRunDesign_clicked)

        self.mMapLayerComboBoxProjectionCentres.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mFieldComboBoxAltControl.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxOmega.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxPhi.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxKappa.setFilters(QgsFieldProxyModel.Numeric)
        self.mMapLayerComboBoxDTM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBoxAoI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.mMapLayerComboBoxCorridor.setFilters(QgsMapLayerProxyModel.LineLayer)
        
        self.pushButtonCancelDesign.clicked.connect(self.on_pushButtonCancelDesign_clicked)
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
            features = lyr.getFeatures()
            for feature in features:
                self.geom_AoI = feature.geometry()
                break
            self.terrain_handler.set_aoi(lyr)

    def on_mMapLayerComboBoxCorridor_layerChanged(self):
        lyr = self.mMapLayerComboBoxCorridor.currentLayer()
        self.CorLine = lyr
        if lyr is not None:
            self.pathLine = self.CorLine.dataProvider().dataSourceUri()
            self.terrain_handler.set_corridor_line(lyr)
        else:
            self.pathLine = None

    def on_tabWidgetBlockCorridor_currentChanged(self):
        if self.tabWidgetBlockCorridor.currentIndex() == 0:
            self.tabBlock = True
            self.tabCorridor = False
        else:
            self.tabBlock = False
            self.tabCorridor = True

    def on_pushButtonRunDesign_clicked(self):
        self.pushButtonCancelDesign.setVisible(True)
        altitude_type = self.comboBoxAltitudeType.currentText()

        if altitude_type == 'One Altitude ASL For Entire Flight':
            run_design_one_altitude(self)
        elif altitude_type == 'Separate Altitude ASL For Each Strip':
            run_design_separate_altitude(self)
        elif altitude_type == 'Terrain Following':
            run_design_terrain_following(self)
        self.pushButtonCancelDesign.setVisible(False)
    
    def on_crs_changed(self, crs):
        self.epsg_code = crs.authid()
        self.crsSelector.setCrs(QgsCoordinateReferenceSystem(f"self.epsg_code"))

    def startWorker_updateAltitude(self, **params):
        worker = Worker(**params)
        thread = QThread(self)
        worker.moveToThread(thread)

        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progressBar.setValue)
        worker.enabled.connect(self.pushButtonRunDesign.setEnabled)
        worker.enabled.connect(self.pushButtonRunControl.setEnabled)

        thread.started.connect(worker.run_altitudeStrip)
        
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, result, group_name):
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if result is not None:
            if group_name == 'flight_design':
                add_layers_to_canvas(result, group_name, self.design_run_counter)
                self.design_run_counter += 1

    def workerError(self, exception, traceback_str):
        QgsMessageLog.logMessage(str(exception), 'Flight Planner', Qgis.Critical)
        QgsMessageLog.logMessage(traceback_str, 'Flight Planner', Qgis.Critical)
        self.pushButtonRunDesign.setEnabled(True)

    def on_pushButtonCancelDesign_clicked(self):
        if hasattr(self, "worker") and self.worker:
            self.worker.killed = True