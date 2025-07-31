from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer, QgsRasterBandStats
from PyQt5.QtGui import QColor

def apply_gsd_style(gsd_layer):
    provider = gsd_layer.dataProvider()
    stats = provider.bandStatistics(1, QgsRasterBandStats.All)
    min_v = stats.minimumValue
    max_v = stats.maximumValue

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
