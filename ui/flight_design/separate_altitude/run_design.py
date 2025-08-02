from ....error_reporting import QgsTraceback
from ....functions import *
from ..altitudes_utils.inputs_validation import validate_inputs
from ..altitudes_utils.initialization import initialize_design_environment
from ..altitudes_utils.flight_parameters import calculate_flight_parameters
from ..altitudes_utils.altitude_calculation import calculate_altitude
from ..altitudes_utils.process_modes import process_block_mode, process_corridor_mode

def run_design_separate_altitude(ui):
    """RunDesign logic for 'Separate Altitude ASL for Each Strip'."""
    ui.pushButtonRunDesign.setEnabled(False)
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

        params = dict(
            pointLayer=pc_lay,
            polygonLayer=photo_lay,
            DTM=ui.DTM,
            altitude_AGL=altitude_AGL,
            crsVectorLayer=ui.crs_vct,
            crsRasterLayer=ui.crs_rst,
            tabWidg=ui.tabCorridor,
            theta=theta,
            distance=dist
        )

        if ui.tabCorridor:
            params['LineRangeList'] = line_buf_list
        else:
            params['Range'] = ui.geom_AoI

        ui.startWorker_updateAltitude(mode="separate", **params)
    except Exception:
        ui.progressBar.setValue(0)
        ui.pushButtonCancelDesign.setVisible(False)
        ui.pushButtonRunDesign.setEnabled(True)
        QgsTraceback()