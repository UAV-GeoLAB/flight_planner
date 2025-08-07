from qgis.PyQt import QtWidgets, uic
from .ui.camera_section import CameraSectionHandler
from .ui.altitude_section import AltitudeSectionHandler
from .ui.terrain_section import TerrainSectionHandler
from .ui.direction_section import DirectionSectionHandler
import os
from .error_reporting import QgsPrint, QgsTraceback, QgsMessBox
from .geoprocessing.layers import add_to_canvas, find_matching_field
from osgeo import gdal
from qgis.core import (
    QgsMapLayerProxyModel, 
    QgsFieldProxyModel, 
    QgsCoordinateReferenceSystem, 
    QgsProject
)
from .ui.flight_design.one_altitude.run_design import run_design_one_altitude
from .ui.flight_design.separate_altitude.run_design import run_design_separate_altitude
from .ui.flight_design.terrain_following.run_design import run_design_terrain_following
from .ui.flight_design.separate_altitude.worker import WorkerSeparate
from .ui.flight_design.terrain_following.worker import WorkerTerrain
from PyQt5.QtCore import QThread
from PyQt5 import QtWidgets
from .ui.quality_control.worker import WorkerControl

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'flight_planner_dialog_base.ui'))

class FlightPlannerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.tabWidget.setCurrentIndex(0)
        """Hide Cancel button"""
        self.pushButtonCancelDesign.setVisible(False)

        """Switch window tabs"""
        self.tabBlock = True
        self.tabCorridor = False
        self.tabWidgetBlockCorridor.currentChanged.connect(self.on_tabWidgetBlockCorridor_currentChanged)
        self.tabWidget.currentChanged.connect(self.on_tabWidget_changed)

        """Initial DTM CRS setting"""
        try:
            self.epsg_code = QgsProject.instance().crs().authid()
            crs = QgsCoordinateReferenceSystem(self.epsg_code)
        except Exception:
            self.epsg_code = "EPSG:2180"
            crs = QgsCoordinateReferenceSystem(self.epsg_code)
        self.crsSelector.setCrs(crs)

        self.design_run_counter = 1
        self.control_run_counter = 1
        
        """GUI handlers part"""
        self.camera_handler = CameraSectionHandler(self)
        self.camera_handler.setup()
        
        self.altitude_handler = AltitudeSectionHandler(self, self.camera_handler)
        self.altitude_handler.setup()

        self.terrain_handler = TerrainSectionHandler(self)
        self.pushButtonGetHeights.clicked.connect(lambda _: self.terrain_handler.on_btn_get_heights_clicked())

        self.direction_handler = DirectionSectionHandler(self.dial, self.spinBoxDirection)
        
        """Fill Altitude Type combobox"""
        self.comboBoxAltitudeType.addItems(["One Altitude ASL For Entire Flight",
            "Separate Altitude ASL For Each Strip",
            "Terrain Following"])

        """Disconnect previous connections to avoid multiple calls"""
        try:
            self.pushButtonRunDesign.clicked.disconnect()
        except TypeError:
            pass
        self.pushButtonRunDesign.clicked.connect(self.on_pushButtonRunDesign_clicked)

        try:
            self.pushButtonRunControl.clicked.disconnect()
        except TypeError:
            pass
        self.pushButtonRunControl.clicked.connect(self.on_pushButtonRunControl_clicked)

        """Filters for comboboxes"""
        self.mMapLayerComboBoxProjectionCentres.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mFieldComboBoxAltControl.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxOmega.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxPhi.setFilters(QgsFieldProxyModel.Numeric)
        self.mFieldComboBoxKappa.setFilters(QgsFieldProxyModel.Numeric)
        self.mMapLayerComboBoxDTM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBoxAoI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.mMapLayerComboBoxCorridor.setFilters(QgsMapLayerProxyModel.LineLayer)
        
        """Handle click of cancel buttons"""
        self.pushButtonCancelDesign.clicked.connect(lambda: self.cancel_worker('design'))
        self.pushButtonCancelControl.clicked.connect(lambda: self.cancel_worker('control'))
        
        """CRS Selector configuration"""
        self.crsSelector.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))
        self.crsSelector.crsChanged.connect(self.on_crs_changed)

        """Quality control: Process automatization"""
        self.radioButtonSeaLevel.toggled.connect(self.on_altitudeTypeChanged)
        self.radioButtonGroundLevel.toggled.connect(self.on_altitudeTypeChanged)
        self._init_default_layers()
    
    def _init_default_layers(self):
        self.on_mMapLayerComboBoxDTM_layerChanged()
        self.on_mMapLayerComboBoxAoI_layerChanged()
        self.on_mMapLayerComboBoxCorridor_layerChanged()
        if self.tabWidget.currentIndex() == 1:
            self.on_mMapLayerComboBoxProjectionCentres_layerChanged()
    
    def on_mMapLayerComboBoxDTM_layerChanged(self):
        """Handle change of DTM layer"""
        lyr = self.mMapLayerComboBoxDTM.currentLayer()
        self.DTM = lyr
        if lyr:
            try:
                self.raster = gdal.Open(lyr.source())
                self.terrain_handler.set_dtm(lyr, self.raster)
            except Exception:
                QgsTraceback()

    def on_mMapLayerComboBoxAoI_layerChanged(self):
        """Handle change of AoI layer"""
        lyr = self.mMapLayerComboBoxAoI.currentLayer()
        self.AreaOfInterest = lyr
        if lyr:
            features = lyr.getFeatures()
            for feature in features:
                self.geom_AoI = feature.geometry()
                break
            self.terrain_handler.set_aoi(lyr)

    def on_mMapLayerComboBoxCorridor_layerChanged(self):
        """Handle change of Corridor line layer"""
        lyr = self.mMapLayerComboBoxCorridor.currentLayer()
        self.CorLine = lyr
        if lyr is not None:
            self.pathLine = self.CorLine.dataProvider().dataSourceUri()
            self.terrain_handler.set_corridor_line(lyr)
        else:
            self.pathLine = None

    def on_tabWidgetBlockCorridor_currentChanged(self):
        """Handle tab change (Block / Corridor)"""
        if self.tabWidgetBlockCorridor.currentIndex() == 0:
            self.tabBlock = True
            self.tabCorridor = False
        else:
            self.tabBlock = False
            self.tabCorridor = True

    def on_tabWidget_changed(self):
        """Handle tab change (Flight Design / Quality Control)"""
        if self.tabWidget.currentIndex() == 1:
            self.on_mMapLayerComboBoxProjectionCentres_layerChanged()

    def on_pushButtonRunDesign_clicked(self):
        """Start proper type of altitude after clicking Run button"""
        altitude_type = self.comboBoxAltitudeType.currentText()
        try:
            if altitude_type == 'One Altitude ASL For Entire Flight':
                run_design_one_altitude(self)
            elif altitude_type == 'Separate Altitude ASL For Each Strip':
                run_design_separate_altitude(self)
            elif altitude_type == 'Terrain Following':
                run_design_terrain_following(self)
        except Exception:
            QgsTraceback()
            self.pushButtonCancelDesign.setVisible(False)
    
    def on_crs_changed(self, crs):
        """Handle change of Coordinate Reference System"""
        self.epsg_code = crs.authid()
        self.crsSelector.setCrs(QgsCoordinateReferenceSystem(self.epsg_code))

    def startWorker_updateAltitude(self, mode, **params):
        """Initialize Workers"""
        self.pushButtonRunDesign.setEnabled(False)

        current_progress = self.progressBar.value()
        params["start_progress"] = current_progress

        if mode == "terrain":
            worker = WorkerTerrain(**params)
        else:
            worker = WorkerSeparate(**params)
        thread = QThread(self)

        worker.moveToThread(thread)

        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progressBar.setValue)
        worker.enabled.connect(self.pushButtonRunDesign.setEnabled)
        worker.enabled.connect(self.pushButtonRunControl.setEnabled)

        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        if mode == "terrain":
            thread.started.connect(worker.run_followingTerrain)
        else:
            thread.started.connect(worker.run_altitudeStrip)
        
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, result, group_name):
        """Generate result after ending work in Workers"""
        self.thread.quit()
        self.thread.wait()

        if result is not None:
            if group_name == 'flight_design':
                add_to_canvas(result, group_name, self.design_run_counter)
                self.design_run_counter += 1

        self.pushButtonRunDesign.setEnabled(True)
        self.pushButtonCancelDesign.setVisible(False)

    def workerError(self, exception, traceback_str):
        """Handle errors in Workers"""
        QgsPrint(str(exception), level="Critical")
        QgsPrint(traceback_str, level="Critical")
        self.pushButtonRunDesign.setEnabled(True)

    def cancel_worker(self, which):
        """Cancel Workers during processing"""
        if which == 'design' and hasattr(self, "worker") and self.worker:
            self.worker.killed = True
        elif which == 'control' and hasattr(self, "worker_control") and self.worker_control:
            self.worker_control.killed = True
            
    def on_mMapLayerComboBoxProjectionCentres_layerChanged(self):
        """Automatic Fields filling after seting layer with Projection Centres"""
        try:
            layer = self.mMapLayerComboBoxProjectionCentres.currentLayer()
            
            def clear_field_layers():
                for combo in [self.mFieldComboBoxAltControl, self.mFieldComboBoxOmega, self.mFieldComboBoxPhi, self.mFieldComboBoxKappa]:
                    combo.setLayer(None)
            
            if not layer:
                clear_field_layers()
                return
            
            self.crs_vct_ctrl = layer.sourceCrs().authid()
            crs = QgsCoordinateReferenceSystem(self.crs_vct_ctrl)
            if crs.isGeographic():
                QgsMessBox(title='Authomatic layer setting failed', 
                           text=f'CRS of Projection Centres layer ({crs}) cannot be geographic.')
                clear_field_layers()
                return

            if self.radioButtonSeaLevel.isChecked():
                alt_type = "asl"
            elif self.radioButtonGroundLevel.isChecked():
                alt_type = "agl"

            field_combos = [
                (self.mFieldComboBoxAltControl, alt_type),
                (self.mFieldComboBoxOmega, "omega"),
                (self.mFieldComboBoxPhi, "phi"),
                (self.mFieldComboBoxKappa, "kappa")
            ]

            for combo, pattern in field_combos:
                combo.setLayer(layer)
                field_name = find_matching_field(layer, pattern)
                if field_name:
                    combo.setField(field_name)
        except Exception:
            QgsTraceback()

    def on_altitudeTypeChanged(self):
        """Automatic set of Altitude Field after change in combobox"""
        layer = self.mFieldComboBoxAltControl.layer()
        if not layer:
            return

        if self.radioButtonSeaLevel.isChecked():
            alt_type = "asl"
        elif self.radioButtonGroundLevel.isChecked():
            alt_type = "agl"
        else:
            alt_type = None

        if alt_type is None:
            return

        field_name = find_matching_field(layer, alt_type)
        if field_name:
            self.mFieldComboBoxAltControl.setField(field_name)

    def on_pushButtonRunControl_clicked(self):
        """Start controlling quality after clicking Run button"""
        proj_centres = self.mMapLayerComboBoxProjectionCentres.currentLayer()
        fields = {
            'Altitude field': self.mFieldComboBoxAltControl.currentField(),
            'Omega field': self.mFieldComboBoxOmega.currentField(),
            'Phi field': self.mFieldComboBoxPhi.currentField(),
            'Kappa field': self.mFieldComboBoxKappa.currentField(),
        }

        if not hasattr(self, 'DTM'):
            QgsMessBox(title='DTM needed', text='You have to load DTM layer')
            return

        if not proj_centres:
            QgsMessBox(title='Error', text='You have to load Projection centres layer')
            return

        for name, value in fields.items():
            if not value:
                QgsMessBox(title='Error', text=f'You have to indicate {name}')
                return
            
        try:
            threshold = self.doubleSpinBoxIterationThreshold.value()
            self.startWorker_control(
                pointLayer=proj_centres,
                hField=fields['Altitude field'],
                omegaField=fields['Omega field'],
                phiField=fields['Phi field'],
                kappaField=fields['Kappa field'],
                camera=self.camera_handler.camera,
                crsVectorLayer=self.crs_vct_ctrl,
                crsRasterLayer=self.crs_vct_ctrl, # ERROR
                DTM=self.DTM,
                raster=self.raster,
                overlap=self.checkBoxOverlapImages.isChecked(),
                gsd=self.checkBoxGSDmap.isChecked(),
                footprint=self.checkBoxFootprint.isChecked(),
                threshold=threshold,
                height_is_ASL=self.radioButtonSeaLevel.isChecked()
            )
            self.pushButtonRunControl.setEnabled(False)
        except Exception:
            QgsTraceback()

    def startWorker_control(self, **params):
        """Initialize Quality Control Worker"""
        worker = WorkerControl(**params)
        thread = QThread(self)
        worker.moveToThread(thread)

        worker.finished.connect(self.workerControlFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progressBarControl.setValue)
        worker.enabled.connect(self.pushButtonRunControl.setEnabled)
        worker.enabled.connect(self.pushButtonRunDesign.setEnabled)

        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.started.connect(worker.run_control)

        thread.start()

        self.thread_control = thread
        self.worker_control = worker

    def workerControlFinished(self, result, group_name):
        """Generate result after ending work in Quality Control Worker"""
        self.thread_control.quit()
        self.thread_control.wait()
        self.thread_control.deleteLater()

        if result is not None and group_name == "quality_control":
            add_to_canvas(result, group_name, self.control_run_counter)
            self.control_run_counter += 1

        self.pushButtonRunControl.setEnabled(True)
        self.pushButtonRunDesign.setEnabled(True)