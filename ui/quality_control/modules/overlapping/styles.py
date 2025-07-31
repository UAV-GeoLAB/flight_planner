from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer
from PyQt5.QtGui import QColor

def create_overlay_renderer(provider, max_value):
    color_ramp = QgsColorRampShader()
    color_ramp.setColorRampType(QgsColorRampShader.Exact)
    items = []
    clr_step = int(255 / max_value)
    for i in range(1, int(max_value) + 1):
        items.append(QgsColorRampShader.ColorRampItem(i, QColor(clr_step * i, clr_step * i, clr_step * i), str(i)))
    color_ramp.setColorRampItemList(items)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(color_ramp)

    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, raster_shader)
    return renderer