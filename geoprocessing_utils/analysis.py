from qgis.analysis import QgsZonalStatistics


def raster_minmax_in_vector(vector, raster):
    """Return max and min value of raster clipped by vector layer."""

    zone_stats = QgsZonalStatistics(vector, raster, 'pre-', 1,
                                    QgsZonalStatistics.Statistics(
                                        QgsZonalStatistics.Min |
                                        QgsZonalStatistics.Max))
    zone_stats.calculateStatistics(None)

    for f in vector.getFeatures():
        min_h = f.attribute('pre-min')
        max_h = f.attribute('pre-max')

    min_idx = vector.fields().lookupField('pre-min')
    max_idx = vector.fields().lookupField('pre-max')
    vector.startEditing()
    vector.deleteAttributes([min_idx, max_idx])
    vector.commitChanges()

    return min_h, max_h
