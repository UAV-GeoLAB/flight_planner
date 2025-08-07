from math import acos, sqrt, pi
import numpy as np
import matplotlib.path as mpltPath
from ..mathgeo_utils.coordinates import pixel2crs, lines_intersection, line

def points_pixel_centroids(geotransform, shape):
    """Return pixel centroids for the raster."""

    upx = geotransform[0]
    upy = geotransform[3]
    xscale = geotransform[1]
    yscale = geotransform[5]
    xskew = geotransform[2]
    yskew = geotransform[4]
    pc = sqrt(xscale ** 2 + yskew ** 2)
    pr = sqrt(yscale ** 2 + xskew ** 2)
    alpha = acos(xscale / pc)

    x_grid = np.arange(0, shape[1]*pc, pc)
    y_grid = np.arange(0, -shape[0]*pr, -pr)
    xv, yv = np.meshgrid(x_grid[:shape[1]], y_grid[:shape[0]])

    xx = xv.reshape((-1, 1))
    yy = yv.reshape((-1, 1))

    x_start = upx + 1 / 2 * pc
    y_start = upy - 1 / 2 * pr
    centroid_x = x_start + np.cos(-alpha)*xx + np.sin(-alpha)*yy
    centroid_y = y_start + -np.sin(-alpha)*xx + np.cos(-alpha)*yy

    return np.hstack((centroid_x, centroid_y))


def overlap_photo(footprint_vertices, geotransform, clipped_DTM_shape):
    """Return logical array of photo's footprint."""

    raster_centroids = points_pixel_centroids(geotransform, clipped_DTM_shape)

    path = mpltPath.Path(footprint_vertices)
    centroids_inside = path.contains_points(raster_centroids)

    logical_array = centroids_inside.reshape((clipped_DTM_shape[0], -1))

    max_row, max_col = np.argwhere(logical_array > 0).max(axis=0)
    min_row, min_col = np.argwhere(logical_array > 0).min(axis=0)

    trimed_logical_array = logical_array[min_row:max_row+1, min_col:max_col+1]

    upper_left_x, upper_left_y = pixel2crs(geotransform, min_col, min_row)
    trimed_geotransform = geotransform[:]
    trimed_geotransform[0] = upper_left_x
    trimed_geotransform[3] = upper_left_y

    return trimed_logical_array, trimed_geotransform


def gsd(DTM, geotransform, Xs, Ys, Zs, Xs_, Ys_, Zs_, f, size_sensor):
    """Return GSD array."""

    vect_vertical = np.array([0, 0, -1])
    vect_camera_axis = [Xs_ - Xs, Ys_ - Ys, Zs_ - Zs]
    t = angle_between_vectors(vect_vertical, vect_camera_axis)
    if t == 0:
        gsd_array = ((Zs - DTM) * size_sensor / f) * 100
    else:
        a, b = line(Ys, Ys_, Xs, Xs_)
        if a != 0:
            a_l_ = -1 / a
        else:
            a_l_ = -1 / 0.000000000000000001

        pxpy = points_pixel_centroids(geotransform, DTM.shape)
        px = pxpy[:, 0]
        py = pxpy[:, 1]

        b_l_ = py - a_l_ * px
        ppx, ppy = lines_intersection(a_l_, b_l_, a, b)
        Z = DTM
        vect_S_pp = np.array([ppx - Xs, ppy - Ys, (Z - Zs).flatten()])

        beta = angle_between_vectors(vect_vertical, vect_S_pp)

        direction = angle_between_vectors((vect_camera_axis[0],
                                           vect_camera_axis[1]),
                                          (vect_S_pp[0],
                                           vect_S_pp[1]))

        correct_beta = np.where(direction >= 90, -beta, beta).reshape(Z.shape)

        W = Zs - Z
        gsd_array = size_sensor * (W/f) * np.cos(np.radians(correct_beta - t)) \
                          / np.cos(np.radians(correct_beta)) * 100
    return gsd_array

def angle_between_vectors(v1, v2):
    """Return angle between two 2D vectors."""
    v1v2 = np.dot(v1, v2)
    lenv1 = np.linalg.norm(v1)
    lenv2 = np.linalg.norm(v2, axis=0)
    g = np.array(v1v2 / (lenv1 * lenv2))
    g[g > 1] = 1
    g[g < -1] = -1
    angle = np.arccos(g) * 180 / pi
    return angle