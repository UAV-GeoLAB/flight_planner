from qgis.core import QgsRasterLayer, QgsProcessingUtils
from osgeo import gdal, osr
import numpy as np
import os
from .styles import apply_gsd_style
from .....mathgeo.coordinates import crs2pixel
def process_gsd(worker, ds_list, ulx_list, uly_list, lrx_list, lry_list, xres, yres):
    """Quality Control: Process gsd_map layer"""
    ulx_fp = min(ulx_list)
    uly_fp = max(uly_list)
    lrx_fp = max(lrx_list)
    lry_fp = min(lry_list)

    cols_fp = int(np.ceil((lrx_fp - ulx_fp) / xres))
    rows_fp = int(np.ceil((lry_fp - uly_fp) / yres))

    final_gsd = np.ones((rows_fp, cols_fp)) * 1000
    geo = [ulx_fp, xres, 0, uly_fp, 0, yres]

    for gsd_array, overlay_array, geot in ds_list:
        if worker.killed:
            worker.handle_cancel()
            return None
        
        c, r = crs2pixel(geo, geot[0] + xres / 2, geot[3] + yres / 2)
        c, r = int(c), int(r)
        rows, cols = overlay_array.shape
        final_gsd[r:r+rows, c:c+cols] = np.minimum(final_gsd[r:r+rows, c:c+cols], gsd_array)

    temp_gsd = os.path.join(QgsProcessingUtils.tempFolder(), 'gsd.tif')
    driver = gdal.GetDriverByName('GTiff')
    ds_gsd = driver.Create(temp_gsd, xsize=cols_fp, ysize=rows_fp, bands=1, eType=gdal.GDT_Float32)
    ds_gsd.GetRasterBand(1).WriteArray(final_gsd)
    ds_gsd.GetRasterBand(1).SetNoDataValue(1000)
    ds_gsd.SetGeoTransform(geo)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(worker.crs_rst.split(":")[1]))
    srs.SetWellKnownGeogCS(worker.crs_rst)
    ds_gsd.SetProjection(srs.ExportToWkt())
    ds_gsd = None

    gsd_layer = QgsRasterLayer(temp_gsd, "gsd_map")
    apply_gsd_style(gsd_layer)
    return gsd_layer