from PyQt5.QtCore import QObject, pyqtSignal
from .modules.processing import process_quality_control

class WorkerControl(QObject):
    """Worker for "Quality Control"."""
    finished = pyqtSignal(object, str)
    error = pyqtSignal(Exception, str)
    progress = pyqtSignal(int)
    enabled = pyqtSignal(bool)

    def __init__(self, **data):
        super().__init__()
        self.layer = data.get('pointLayer')
        self.crs_vct = data.get('crsVectorLayer')
        self.DTM = data.get('DTM')
        self.raster = data.get('raster')
        self.crs_rst = data.get('crsRasterLayer')

        self.height_is_ASL = data.get('height_is_ASL')
        self.height_f = data.get('hField')
        self.omega_f = data.get('omegaField')
        self.phi_f = data.get('phiField')
        self.kappa_f = data.get('kappaField')

        self.camera = data.get('camera')
        self.overlap_bool = data.get('overlap')
        self.gsd_bool = data.get('gsd')
        self.footprint_bool = data.get('footprint')
        
        self.threshold = data.get('threshold')
        self.theta = data.get('theta')
        self.dist = data.get('distance')
        self.killed = False

    def run_control(self):
        """Main worker function"""
        process_quality_control(self)

    def handle_cancel(self):
        """Handle pressed Cancel button"""
        self.progress.emit(0)
        self.enabled.emit(True)
        self.finished.emit(None, "quality_control")