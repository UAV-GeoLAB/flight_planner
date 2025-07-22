from qgis.core import QgsVectorLayer
from qgis.analysis import QgsZonalStatistics
from qgis import processing
from math import ceil, fabs, isnan
from pyproj import Transformer
from ..utils import transf_coord


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
    band = 1

    provider = raster_layer.dataProvider()
    block = provider.block(band, extent, int(extent.width()), int(extent.height()))

    for row in range(block.height()):
        for col in range(block.width()):
            val = block.value(col, row)
            if val is None or (isinstance(val, float) and isnan(val)):
                raise ValueError("Raster contains None or NaN values within the polygon AoI.")
            
def is_poligon_inside_raster(vlayer, dtm_layer):
    params_calc = {
        'INPUT_A': dtm_layer,
        'BAND_A': 1,
        'FORMULA': '1',
        'OUTPUT': 'TEMPORARY_OUTPUT',
        'RTYPE': 0,
        'NO_DATA': None,
        'EXTENT': 'ignore'
    }
    raster_ones = processing.run("gdal:rastercalculator", params_calc)['OUTPUT']
    
    params_polygonize = {
        'INPUT': raster_ones,
        'BAND': 1,
        'FIELD': 'DN',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }
    raster_polygon = processing.run("gdal:polygonize", params_polygonize)['OUTPUT']
    
    raster_polygon_layer = QgsVectorLayer(raster_polygon, "raster_polygon", "ogr")
    
    raster_geom = None
    for feat in raster_polygon_layer.getFeatures():
        geom = feat.geometry()
        raster_geom = geom if raster_geom is None else raster_geom.combine(geom)

    features_outside = []
    for f in vlayer.getFeatures():
        if not raster_geom.contains(f.geometry()):
            features_outside.append(f.id())
    
    if features_outside:
        raise ValueError(f"Obiekty nie leżą CAŁKOWICIE wewnątrz zasięgu danych rastra")

    return list(vlayer.getFeatures())

def minmaxheight(vlayer, dtm_layer):
    features_inside = is_poligon_inside_raster(vlayer, dtm_layer)
    temp_layer = QgsVectorLayer(f"Polygon?crs={vlayer.crs().authid()}", "temp", "memory")
    temp_layer.dataProvider().addFeatures(features_inside)
    
    stats = QgsZonalStatistics(
        temp_layer, 
        dtm_layer,
        "pre_",
        1,
        QgsZonalStatistics.Min | QgsZonalStatistics.Max
    )
    
    if stats.calculateStatistics(None) != 0:
        raise RuntimeError("Błąd obliczania statystyk strefowych.")

    gmin, gmax = None, None
    for f in temp_layer.getFeatures():
        try:
            mn, mx = float(f["pre_min"]), float(f["pre_max"])
            gmin = mn if gmin is None or mn < gmin else gmin
            gmax = mx if gmax is None or mx > gmax else gmax
        except:
            continue
    
    if gmin is None or gmax is None:
        raise ValueError("Nie udało się określić min/max wartości z rastra.")
    
    return gmin, gmax