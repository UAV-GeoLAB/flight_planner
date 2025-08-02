from ....error_reporting import QgsPrint, QgsMessBox

def validate_inputs(ui):
    """Validate inputs connected with camera, and AoI / Corridor line"""
    if not hasattr(ui.camera_handler, 'camera') or ui.camera_handler.camera is None:
        QgsPrint("Camera is not configured properly.", level="Critical")
        return False

    if ui.tabBlock and (not hasattr(ui, 'AreaOfInterest') or ui.AreaOfInterest is None):
        QgsMessBox('AoI needed', 'You have to load Area of Interest layer')
        return False
    elif ui.tabCorridor and (not hasattr(ui, "pathLine") or ui.pathLine is None):
        QgsMessBox('Corridor line needed', 'You have to load Corridor line layer')
        return False

    return True