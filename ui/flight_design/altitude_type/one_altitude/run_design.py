from .....utils import show_error, show_info, traceback_error
from .....functions import *
from ._inputs_validation import validate_inputs
from ._initialization import initialize_crs_and_progressbar
from ._flight_parameters import calculate_flight_parameters
from ._altitude_calculation import calculate_altitude
from ._process_modes import process_block_mode, process_corridor_mode
from ._enrichments import enrich_projection_centres_with_agl
from ._layer_styling import prepare_and_style_layers

def run_design_one_altitude(ui):
    ui.pushButtonRunDesign.setEnabled(False)
    try:
        if not validate_inputs(ui):
            return

        initialize_crs_and_progressbar(ui)

        altitude_ASL = calculate_altitude(ui)
        Bx, By, len_along, len_across = calculate_flight_parameters(ui)

        if ui.tabBlock:
            pc_lay, photo_lay = process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL)
        elif ui.tabCorridor:
            pc_lay, photo_lay = process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL)

        enrich_projection_centres_with_agl(ui, pc_lay)
        prepare_and_style_layers(ui, pc_lay, photo_lay)

    except Exception:
        ui.progressBar.setValue(0)
        traceback_error()
    finally:
        ui.pushButtonRunDesign.setEnabled(True)