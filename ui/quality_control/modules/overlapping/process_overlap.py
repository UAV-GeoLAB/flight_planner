from qgis.core import QgsRasterLayer, QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer, QgsRasterBandStats, QgsProcessingUtils
from PyQt5.QtGui import QColor
from osgeo import gdal, osr
from .....functions import crs2pixel
import numpy as np
import os
from .styles import create_overlay_renderer

def process_overlap(worker, ds_list, ulx_list, uly_list, lrx_list, lry_list, xres, yres):
    ulx_fp = min(ulx_list)
    uly_fp = max(uly_list)
    lrx_fp = max(lrx_list)
    lry_fp = min(lry_list)

    cols_fp = int(np.ceil((lrx_fp - ulx_fp) / xres))
    rows_fp = int(np.ceil((lry_fp - uly_fp) / yres))

    final_overlay = np.zeros((rows_fp, cols_fp))
    geo = [ulx_fp, xres, 0, uly_fp, 0, yres]

    for gsd_array, overlay_array, geot in ds_list:
        if worker.killed:
            worker.handle_cancel()
            return None
        
        c, r = crs2pixel(geo, geot[0] + xres / 2, geot[3] + yres / 2)
        c, r = int(c), int(r)
        rows, cols = overlay_array.shape
        final_overlay[r:r+rows, c:c+cols] += overlay_array

    tmp_overlay = os.path.join(QgsProcessingUtils.tempFolder(), 'overlay.tif')
    driver = gdal.GetDriverByName('GTiff')
    ds_overlay = driver.Create(tmp_overlay, xsize=cols_fp, ysize=rows_fp, bands=1, eType=gdal.GDT_Float32)
    ds_overlay.GetRasterBand(1).WriteArray(final_overlay)
    ds_overlay.GetRasterBand(1).SetNoDataValue(0)
    ds_overlay.SetGeoTransform(geo)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(worker.crs_rst.split(":")[1]))
    srs.SetWellKnownGeogCS(worker.crs_rst)
    ds_overlay.SetProjection(srs.ExportToWkt())
    ds_overlay = None

    overlay_layer = QgsRasterLayer(tmp_overlay, "overlapping")
    overlay_pr = overlay_layer.dataProvider()
    stats = overlay_pr.bandStatistics(1, QgsRasterBandStats.All)
    max_v = stats.maximumValue

    renderer = create_overlay_renderer(overlay_pr, max_v)
    overlay_layer.setRenderer(renderer)
    overlay_layer.triggerRepaint()

    return overlay_layer
