from .....utils import show_error, show_info

def validate_inputs(ui):
    if not hasattr(ui.camera_handler, 'camera') or ui.camera_handler.camera is None:
        show_error("Camera is not configured properly.", level="Critical")
        return False

    if ui.tabBlock and (not hasattr(ui, 'AreaOfInterest') or ui.AreaOfInterest is None):
        show_info('AoI needed', 'You have to load Area of Interest layer')
        return False
    elif ui.tabCorridor and (not hasattr(ui, "pathLine") or ui.pathLine is None):
        show_info('Corridor line needed', 'You have to load Corridor line layer')
        return False

    return True