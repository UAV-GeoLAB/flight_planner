def annotate_segment_features(pc_lay, photo_lay, segment, segment_nr):
    pc_lay.startEditing()
    photo_lay.startEditing()
    feature_id = 1
    for strip_nr, photos_nr in segment.items():
        for photo_nr in photos_nr:
            st_nr = '%04d' % strip_nr
            ph_nr = '%05d' % photo_nr
            pc_lay.changeAttributeValue(feature_id, 0, st_nr)
            pc_lay.changeAttributeValue(feature_id, 1, ph_nr)
            pc_lay.changeAttributeValue(feature_id, 9, segment_nr)
            photo_lay.changeAttributeValue(feature_id, 0, st_nr)
            photo_lay.changeAttributeValue(feature_id, 1, ph_nr)
            feature_id += 1
    pc_lay.commitChanges()
    photo_lay.commitChanges()