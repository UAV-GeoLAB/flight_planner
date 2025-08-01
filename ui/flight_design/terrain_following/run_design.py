from ....error_reporting import QgsTraceback
from ....functions import *
from ..altitudes_utils.inputs_validation import validate_inputs
from ..altitudes_utils.initialization import initialize_design_environment
from ..altitudes_utils.flight_parameters import calculate_flight_parameters
from ..altitudes_utils.altitude_calculation import calculate_altitude
from ..altitudes_utils.process_modes import process_block_mode, process_corridor_mode

def run_design_terrain_following(ui):
    """RunDesign logic for 'Terrain Following'."""
    try:
        if not validate_inputs(ui):
            return
        
        initialize_design_environment(ui)

        altitude_ASL, altitude_AGL = calculate_altitude(ui)
        Bx, By, len_along, len_across = calculate_flight_parameters(ui)

        if ui.tabBlock:
            pc_lay, photo_lay, theta, dist = process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL)
        elif ui.tabCorridor:
            pc_lay, photo_lay, line_buf_list, theta, dist = process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL)

        ui.startWorker_updateAltitude(mode='terrain',
                                      pointLayer=pc_lay,
                                      crsVectorLayer=ui.crs_vct,
                                      raster=ui.raster,
                                      polygonLayer=photo_lay,
                                      crsRasterLayer=ui.crs_rst,
                                      tolerance = ui.doubleSpinBoxTolerance.value(),
                                      altitude_AGL=altitude_AGL,
                                      epsg_code=ui.epsg_code)                     
    except Exception:
        ui.progressBar.setValue(0)
        ui.pushButtonCancelDesign.setVisible(False)
        ui.pushButtonRunDesign.setEnabled(True)
        QgsTraceback()