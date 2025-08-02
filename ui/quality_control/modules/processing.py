import traceback
from .footprints.process_footprints import process_footprints
from .overlapping.process_overlap import process_overlap
from .gsd_map.process_gsd import process_gsd

def process_quality_control(worker):
    """Process controlling quality and generating layers"""
    result = []
    try:
        func_output = process_footprints(worker)
        if func_output is None:
            return
        footprint_lay, ds_list, ulx_list, uly_list, lrx_list, lry_list, xres, yres = func_output

        if worker.overlap_bool:
            overlap_layer = process_overlap(worker, ds_list,
                                            ulx_list, uly_list,
                                            lrx_list, lry_list,
                                            xres, yres)
            if overlap_layer is not None:
                result.append(overlap_layer)

        if worker.gsd_bool:
            gsd_layer = process_gsd(worker, ds_list,
                                    ulx_list, uly_list, 
                                    lrx_list, lry_list,
                                    xres, yres)
            if gsd_layer is not None:
                result.append(gsd_layer)

        if worker.footprint_bool:
            if footprint_lay is not None:
                result.append(footprint_lay)

        worker.progress.emit(100)
        worker.finished.emit(result, "quality_control")
        worker.enabled.emit(True)
    except Exception as e:
        worker.error.emit(e, traceback.format_exc())
        worker.enabled.emit(True)
