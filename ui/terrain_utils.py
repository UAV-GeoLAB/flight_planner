from qgis.core import QgsVectorLayer
from qgis.analysis import QgsZonalStatistics
from qgis import processing
from math import ceil, fabs, isnan
from pyproj import Transformer
from ..mathgeo.coordinates import transf_coord
from ..error_reporting import QgsMessBox


def create_buffer_around_line(path_line, gdal_ds, dtm_layer, buffer_value):
    """Creates a buffer polygon around a corridor line 
    and returns the buffered layer and minimum buffer."""
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
    """Verifies that the raster has valid values inside the AoI."""
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
    """Verifies whether all features in a vector layer are fully inside the extent of a raster"""
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
        message = "AoI does not lie entirely\nwithin the extent of the DTM data."
        QgsMessBox(title="AoI not in DTM", text=message, level="Critical")
        raise ValueError(message)

    return list(vlayer.getFeatures())

def z_at_3d_line(pnt, start_pnt, end_pnt):
    """Return "z" coordinate for point with known x,y
    lying on line in space defined by start and end points.
    """
    x1, y1, z1 = start_pnt
    x2, y2, z2 = end_pnt
    x, y = pnt[:2]

    if x1 != x2:
        t = (x - x1) / (x2 - x1)
    else:
        t = (y - y1) / (y2 - y1)
    z = t * (z2 - z1) + z1
    return z


def simplify_profile(vertices, epsilon):
    """Reduces the number of vertices in the line, keeping its main shape.
    It is based on the Douglas-Peucker simplification algorithm but
    with the vertical distance instead of perpendicular.
    """
    hmax = 0.0
    index = 0
    for i in range(1, len(vertices) - 1):
        z = z_at_3d_line(vertices[i], vertices[0], vertices[-1])
        h = abs(z - vertices[i][2])
        if h > hmax:
            index = i
            hmax = h

    if hmax >= epsilon:
        results = simplify_profile(vertices[:index+1], epsilon)[:-1]\
                  + simplify_profile(vertices[index:], epsilon)
    else:
        results = [vertices[0], vertices[-1]]

    return results

def clipped_raster_minmax(vlayer, dtm_layer):
    """Calculates minimum and maximum elevation values from DTM"""
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
        raise RuntimeError("Error in calculating stats.")

    gmin, gmax = None, None
    for f in temp_layer.getFeatures():
        try:
            mn, mx = float(f["pre_min"]), float(f["pre_max"])
            gmin = mn if gmin is None or mn < gmin else gmin
            gmax = mx if gmax is None or mx > gmax else gmax
        except:
            continue
    
    if gmin is None or gmax is None:
        raise ValueError("Could not determine min/max values from raster.")
    
    return gmin, gmax


