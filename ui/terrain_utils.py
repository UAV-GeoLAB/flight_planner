from qgis.core import QgsRectangle, QgsVectorLayer
from qgis.analysis import QgsZonalStatistics
from qgis import processing
from math import ceil, fabs, isnan
from pyproj import Transformer
from ..utils import transf_coord

def filter_features_inside_raster(vlayer, raster_layer):
    r_extent: QgsRectangle = raster_layer.extent()
    return [f for f in vlayer.getFeatures()
            if r_extent.contains(f.geometry().boundingBox())]

def create_buffer_around_line(path_line, gdal_ds, dtm_layer, buffer_value):
    gt = gdal_ds.GetGeoTransform()
    px_w, px_h = gt[1], -gt[5]
    ulx, uly = gt[0], gt[3]
    ulx_n, uly_n = ulx + px_w, uly + px_h

    crs_rst = dtm_layer.crs().authid()
    crs_vec = path_line.sourceCrs().authid()
    if crs_rst != crs_vec:
        tf = Transformer.from_crs(crs_rst, crs_vec, always_xy=True)
        ulx, uly = transf_coord(tf, ulx, uly)
        ulx_n, uly_n = transf_coord(tf, ulx_n, uly_n)

    min_buf = max(ceil(fabs(ulx_n - ulx)), ceil(fabs(uly_n - uly)))

    params = {
        "INPUT": path_line,
        "DISTANCE": buffer_value,
        "SEGMENTS": 5,
        "END_CAP_STYLE": 0,
        "JOIN_STYLE": 0,
        "MITER_LIMIT": 2,
        "DISSOLVE": False,
        "OUTPUT": "TEMPORARY_OUTPUT",
    }
    out = processing.run("native:buffer", params)["OUTPUT"]
    return out, min_buf

def check_raster_values_on_polygon(raster_layer, polygon_geom):
    extent = polygon_geom.boundingBox()
    band = 1  # zakładamy pasmo 1, można parametryzować

    provider = raster_layer.dataProvider()
    block = provider.block(band, extent, int(extent.width()), int(extent.height()))

    for row in range(block.height()):
        for col in range(block.width()):
            val = block.value(col, row)
            if val is None or (isinstance(val, float) and isnan(val)):
                raise ValueError("Raster contains None or NaN values within the polygon AoI.")
            
def minmaxheight(vlayer, dtm_layer):
    feats = filter_features_inside_raster(vlayer, dtm_layer)
    if not feats:
        raise ValueError("No vector features lie entirely within the raster extent.")

    temp = QgsVectorLayer(f"Polygon?crs={vlayer.crs().authid()}",
                          "temp", "memory")
    temp.dataProvider().addFeatures(feats)
    temp.updateExtents()

    stats = QgsZonalStatistics(
        temp, 
        dtm_layer,
        "pre_",
        1,
        QgsZonalStatistics.Min | QgsZonalStatistics.Max
    )
    if stats.calculateStatistics(None) != 0:
        raise RuntimeError("Zonal statistics calculation failed.")

    gmin, gmax = None, None
    for f in temp.getFeatures():
        try:
            mn, mx = float(f["pre_min"]), float(f["pre_max"])
            gmin = mn if gmin is None or mn < gmin else gmin
            gmax = mx if gmax is None or mx > gmax else gmax
        except Exception:
            continue

    if gmin is None or gmax is None:
        raise ValueError("Could not determine min/max values from raster.")
    return gmin, gmax