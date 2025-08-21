from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer, QgsRasterBandStats, Qgis
from PyQt5.QtGui import QColor
import numpy as np

def apply_gsd_style(gsd_layer):
    provider = gsd_layer.dataProvider()
    block = provider.block(1, gsd_layer.extent(), gsd_layer.width(), gsd_layer.height())

    min_v = float('inf')
    max_v = float('-inf')
    has_data = False
    no_data_value = provider.sourceNoDataValue(1)
    for row in range(block.height()):
        for col in range(block.width()):
            value = block.value(row, col)
            if value != no_data_value and not np.isnan(value):
                has_data = True
                if value < min_v:
                    min_v = value
                if value > max_v:
                    max_v = value

    if not has_data:
        min_v = 0.0
        max_v = 1.0

    color_ramp = QgsColorRampShader()
    color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
    items = [
        QgsColorRampShader.ColorRampItem(min_v, QColor(0, 255, 0), str(min_v)),
        QgsColorRampShader.ColorRampItem(max_v, QColor(255, 0, 0), str(max_v))
    ]
    color_ramp.setColorRampItemList(items)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(color_ramp)

    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, raster_shader)
    renderer.setClassificationMin(min_v)
    renderer.setClassificationMax(max_v)

    gsd_layer.setRenderer(renderer)
    gsd_layer.triggerRepaint()
