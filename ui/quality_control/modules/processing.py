import traceback
from .footprints.process_footprints import process_footprints
from .overlapping.process_overlap import process_overlap
from .gsd_map.process_gsd import process_gsd

def process_quality_control(worker):
    result = []
    try:
        footprint_lay, ds_list, ulx_list, uly_list, lrx_list, lry_list, xres, yres = process_footprints(worker)

        if worker.overlap_bool:
            overlap_layer = process_overlap(worker, ds_list,
                                            ulx_list, uly_list,
                                            lrx_list, lry_list,
                                            xres, yres)
            result.append(overlap_layer)

        if worker.gsd_bool:
            gsd_layer = process_gsd(worker, ds_list,
                                    ulx_list, uly_list, 
                                    lrx_list, lry_list,
                                    xres, yres)
            result.append(gsd_layer)

        if worker.footprint_bool:
            result.append(footprint_lay)

        worker.progress.emit(100)
        worker.finished.emit(result, "quality_control")
        worker.enabled.emit(True)
    except Exception as e:
        worker.error.emit(e, traceback.format_exc())
        worker.enabled.emit(True)
