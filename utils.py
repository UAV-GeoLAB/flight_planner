import traceback
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import QMessageBox


def traceback_error():
    QgsMessageLog.logMessage('\n' + traceback.format_exc(), 'Flight Planner', Qgis.Critical)

def show_error(text="Error in process", level="Critical"):
    if level == "Critical":
        qgis_level = Qgis.Critical
    elif level == "Warning":
        qgis_level = Qgis.Warning
    elif level == "Info":
        qgis_level = Qgis.Info
    elif level == "Success":
        qgis_level = Qgis.Success
    else:
        qgis_level = Qgis.Info

    QgsMessageLog.logMessage(text, 'Flight Planner', qgis_level)

def show_info(title="Flight Planner", text="Information", level="Information"):
    if level == "Information":
        QMessageBox.information(None, title, text)
    elif level == "Critical":
        QMessageBox.critical(None, title, text)
    elif level == "Warning":
        QMessageBox.warning(None, title, text)
    else:
        QMessageBox.information(None, title, text)

def transf_coord(transformer, x, y):
    """Transform coordinates between two CRS."""
    x_transformed, y_transformed = transformer.transform(x, y)
    return x_transformed, y_transformed
