import numpy as np
from .....functions import transf_coord, crs2pixel, pixel2crs

def clip_raster(ds, xyf, R, Xs, Ys, Zs, Z_min, trans_v_r, crs_rst, crs_vct):
    """Return DTM clipped by bounding box of photo. Range of bounding box
     is derived from photo's Exterior Orientation Parameters, camera parameters
     and minimum height of DTM"""

    DTM_array = ds.GetRasterBand(1).ReadAsArray()
    focal = xyf[0, 2]
    img_corners = np.vstack(([0, 0, focal], xyf))

    X_min = Xs + (Z_min - Zs) * np.divide(np.dot(img_corners, R[0]),
                                          np.dot(img_corners, R[2]))
    Y_min = Ys + (Z_min - Zs) * np.divide(np.dot(img_corners, R[1]),
                                          np.dot(img_corners, R[2]))

    X_pc, Y_pc = X_min[0], Y_min[0]
    buffer = max(((X_pc - X_min[1:])**2 + (Y_pc - Y_min[1:])**2)**0.5)

    max_range_X = X_pc + buffer
    min_range_X = X_pc - buffer
    max_range_Y = Y_pc + buffer
    min_range_Y = Y_pc - buffer
    range = np.array([[min_range_X, max_range_Y],
                      [min_range_X, min_range_Y],
                      [max_range_X, min_range_Y],
                      [max_range_X, max_range_Y]
                      ])

    if crs_vct != crs_rst:
        X, Y = transf_coord(trans_v_r, range[:, 0], range[:, 1])
        cols, rows = crs2pixel(ds.GetGeoTransform(), X, Y)
    else:
        cols, rows = crs2pixel(ds.GetGeoTransform(), range[:, 0], range[:, 1])

    upper_left_c, upper_left_r = int(min(cols)//1), int(min(rows)//1)
    bottom_right_c, bottom_right_r = int(max(cols)//1), int(max(rows)//1)

    if upper_left_r < 0:
        upper_left_r = 0
    if upper_left_c < 0:
        upper_left_c = 0

    if bottom_right_r > DTM_array.shape[0]:
        bottom_right_r = DTM_array.shape[0]
    if bottom_right_c > DTM_array.shape[1]:
        bottom_right_c = DTM_array.shape[1]

    x0, y0 = pixel2crs(ds.GetGeoTransform(), upper_left_c, upper_left_r)
    clipped_DTM = np.array(DTM_array[upper_left_r: bottom_right_r+1,
                           upper_left_c: bottom_right_c+1])
    updated_geotransform = list(ds.GetGeoTransform())
    updated_geotransform[0] = x0
    updated_geotransform[3] = y0

    return clipped_DTM, updated_geotransform