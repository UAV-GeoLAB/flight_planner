from qgis.core import QgsPointXY
from pyproj import Transformer

def enrich_projection_centres_with_agl(ui, pc_lay):
    """Enrich projection centres layer with altitude AGL"""
    if not hasattr(ui, 'DTM'):
        return

    if ui.crs_rst != ui.crs_vct:
        crs_from = ui.crs_vct.authid()
        crs_to = ui.crs_rst.authid()

        if not crs_to:
            crs_to = ui.crs_rst.toWkt()
        
        transf_vct_rst = Transformer.from_crs(crs_from, crs_to, always_xy=True)

    feats = pc_lay.getFeatures()
    pc_lay.startEditing()
    for f in feats:
        x, y = f.geometry().asPoint().x(), f.geometry().asPoint().y()
        if ui.crs_rst != ui.crs_vct:
            x, y = transf_vct_rst.transform(x, y)

        altitude_ASL_f = f.attribute('Alt. ASL [m]')
        terrain_height, _ = ui.DTM.dataProvider().sample(QgsPointXY(x, y), 1)
        altitude_AGL_f = altitude_ASL_f - terrain_height
        pc_lay.changeAttributeValue(f.id(), 5, round(altitude_AGL_f, 2))
    pc_lay.commitChanges()
    ui.progressBar.setValue(70)