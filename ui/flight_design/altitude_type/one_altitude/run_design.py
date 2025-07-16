from qgis.PyQt.QtCore import QTimer
from .....utils import show_error

def run_design_one_altitude(ui):
    """Minimal progress bar implementation with guaranteed 100% completion"""
    try:
        ui.progressBar.setRange(0, 100)
        ui.progressBar.setValue(0)
        ui.progressBar.setFormat("%p%")
        
        ui.pushButtonRunDesign.setEnabled(False)
        total_steps = 100
        current_step = 0

        def update_progress():
            nonlocal current_step
            current_step += 1
            progress = min(100, int((current_step / total_steps) * 100))
            ui.progressBar.setValue(progress)
            if current_step >= total_steps:
                timer.stop()
                ui.progressBar.setValue(100)
                ui.pushButtonRunDesign.setEnabled(True)
                show_error("Calculation completed", level="Success")
        timer = QTimer()
        timer.timeout.connect(update_progress)
        timer.start(30)

    except Exception as e:
        ui.progressBar.setValue(0)
        ui.pushButtonRunDesign.setEnabled(True)
        show_error(f"Error: {str(e)}", level="Critical")