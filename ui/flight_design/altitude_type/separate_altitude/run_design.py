from .....utils import traceback_error
from .....functions import *
from ..altitudes_utils.inputs_validation import validate_inputs
from ..altitudes_utils.initialization import initialize_crs_and_progressbar
from ..altitudes_utils.flight_parameters import calculate_flight_parameters
from ..altitudes_utils.altitude_calculation import calculate_altitude
from ..altitudes_utils.process_modes import process_block_mode, process_corridor_mode
from ..altitudes_utils.enrichments import enrich_projection_centres_with_agl
from ..altitudes_utils.layer_styling import prepare_and_style_layers

def run_design_separate_altitude(ui):
    ui.pushButtonRunDesign.setEnabled(False)
    try:
        if not validate_inputs(ui):
            return

        initialize_crs_and_progressbar(ui)

        altitude_ASL, altitude_AGL = calculate_altitude(ui)
        Bx, By, len_along, len_across = calculate_flight_parameters(ui)

        if ui.tabBlock:
            pc_lay, photo_lay, theta, dist = process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL)
        elif ui.tabCorridor:
            pc_lay, photo_lay, theta, dist = process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL)

        if ui.tabCorridor:
            ui.startWorker_updateAltitude(
                pointLayer=pc_lay,
                polygonLayer=photo_lay,
                DTM=ui.DTM,
                altitude_AGL=altitude_AGL,
                crsVectorLayer=ui.crs_vct,
                crsRasterLayer=ui.crs_rst,
                tabWidg=ui.tabCorridor,
                LineRangeList=ui.line_buf_list,
                theta=theta,
                distance=dist
            )
        else:
            ui.startWorker_updateAltitude(
                pointLayer=pc_lay,
                polygonLayer=photo_lay,
                DTM=ui.DTM,
                altitude_AGL=altitude_AGL,
                crsVectorLayer=ui.crs_vct,
                crsRasterLayer=ui.crs_rst,
                tabWidg=ui.tabCorridor,
                Range=ui.geom_AoI,
                theta=theta,
                distance=dist
            )
    except Exception:
        ui.progressBar.setValue(0)
        traceback_error()
    finally:
        ui.pushButtonRunDesign.setEnabled(True)