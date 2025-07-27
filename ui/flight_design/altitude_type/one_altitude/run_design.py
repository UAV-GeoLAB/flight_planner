from .....utils import QgsTraceback
from .....functions import *
from ..altitudes_utils.inputs_validation import validate_inputs
from ..altitudes_utils.initialization import initialize_crs_and_progressbar
from ..altitudes_utils.flight_parameters import calculate_flight_parameters
from ..altitudes_utils.altitude_calculation import calculate_altitude
from ..altitudes_utils.process_modes import process_block_mode, process_corridor_mode
from ..altitudes_utils.enrichments import enrich_projection_centres_with_agl
from ..altitudes_utils.layer_styling import prepare_and_style_layers

def run_design_one_altitude(ui):
    ui.pushButtonRunDesign.setEnabled(False)
    try:
        if not validate_inputs(ui):
            return

        initialize_crs_and_progressbar(ui)

        altitude_ASL, _ = calculate_altitude(ui)
        Bx, By, len_along, len_across = calculate_flight_parameters(ui)

        if ui.tabBlock:
            pc_lay, photo_lay, _, _ = process_block_mode(ui, Bx, By, len_along, len_across, altitude_ASL)
        elif ui.tabCorridor:
            pc_lay, photo_lay, _, _ = process_corridor_mode(ui, Bx, By, len_along, len_across, altitude_ASL)

        enrich_projection_centres_with_agl(ui, pc_lay)
        prepare_and_style_layers(ui, pc_lay, photo_lay)

    except Exception:
        ui.progressBar.setValue(0)
        QgsTraceback()
    finally:
        ui.pushButtonRunDesign.setEnabled(True)