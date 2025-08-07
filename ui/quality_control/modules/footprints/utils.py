import numpy as np
from .....mathgeo.coordinates import crs2pixel, pixel2crs, transf_coord
import scipy.ndimage as ndimage

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


def ground_edge_points(R, Z, threshold, xyf, Xs, Ys, Zs,
                       Z_DTM, geotransform, crs_DTM, crs_pc, transformer):
    """Return ground coordinates of points representing edges of photo."""

    XY = np.zeros((xyf.shape[0], 2))
    XY_prev = np.ones((xyf.shape[0], 2)) * 1000
    Z = np.ones(xyf.shape[0]) * Z
    counter = 0

    while not threshold_reached(XY, XY_prev, threshold):
        XY_prev = np.array(XY)

        X = Xs + (Z - Zs) * np.divide(np.dot(xyf, R[0]), np.dot(xyf, R[2]))
        Y = Ys + (Z - Zs) * np.divide(np.dot(xyf, R[1]), np.dot(xyf, R[2]))
        XY = np.column_stack((X, Y))

        if crs_DTM == crs_pc:
            column, row = crs2pixel(geotransform, X, Y)
        else:
            X_DTM, Y_DTM = transf_coord(transformer, X, Y)
            column, row = crs2pixel(geotransform, X_DTM, Y_DTM)

        rc_array = np.column_stack((row, column)).T
        Z = ndimage.map_coordinates(Z_DTM, rc_array, output=float)

        if counter > 100:
            break
        counter += 1

    return XY


def threshold_reached(xy, xy_previous, threshold):
    """Check if distance between coordinates from iteration i and i-1
    is less than given threshold."""
    dx2_dy2 = (xy - xy_previous)**2
    d = (dx2_dy2[:, 0] + dx2_dy2[:, 1])**0.5
    return all(d < threshold)

def image_edge_points(camera, Z, Zs, mean_res):
    """Create a list of coordinates of points that represent the edges
    of the image in the image's coordinate system."""
    # approximate ground size Lx, Ly of the image
    W = Zs - Z
    Ly = camera.pixels_across_track * camera.sensor_size * W / camera.focal_length
    Lx = camera.pixels_along_track * camera.sensor_size * W / camera.focal_length
    # number of points along the edges of the image
    num_y = Ly / mean_res
    num_x = Lx / mean_res

    # max x and y coordinate of the image
    x_max = camera.sensor_size * camera.pixels_along_track / 2
    y_max = camera.sensor_size * camera.pixels_across_track / 2
    # x or y coordinates to build later [x, y] edges
    y_vertical = np.linspace(-y_max, y_max, int(num_y)).reshape(-1, 1)
    x_horizontal = np.linspace(-x_max, x_max, int(num_x)).reshape(-1, 1)
    x_vertical = np.ones(int(num_y)).reshape(-1, 1)
    y_horizontal = np.ones(int(num_x)).reshape(-1, 1)

    # coordinates of points, that represent 4 edges of image
    left_edge = np.hstack((x_vertical * -x_max, y_vertical))
    top_edge = np.hstack((x_horizontal, y_horizontal * y_max))
    right_edge = np.hstack((x_vertical * x_max, y_vertical * -1))
    bottom_edge = np.hstack((x_horizontal * -1, y_horizontal * -y_max))
    xy = np.vstack((left_edge, top_edge, right_edge, bottom_edge))
    xyf = np.append(xy, np.ones((xy.shape[0], 1)) * -camera.focal_length, axis=1)

    return xyf