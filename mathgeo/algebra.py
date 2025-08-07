import numpy as np
from .coordinates import line 
from qgis.core import Qgis

from math import (
    cos,
    sin,
    radians,
    tan,
    sqrt,
    fabs,
    pi
)

def rotation_matrix(omega, phi, kappa):
    """Return rotation matrix."""
    phi = radians(phi)
    omega = radians(omega)
    kappa = radians(kappa)

    R = np.array([
        [cos(phi) * cos(kappa), -cos(phi) * sin(kappa), sin(phi)],
        [sin(omega) * sin(phi) * cos(kappa) + cos(omega) * sin(kappa),
         -sin(omega) * sin(phi) * sin(kappa) + cos(omega) * cos(kappa),
         -sin(omega) * cos(phi)],
        [-cos(omega) * sin(phi) * cos(kappa) + sin(omega) * sin(kappa),
         cos(omega) * sin(phi) * sin(kappa) + sin(omega) * cos(kappa),
         cos(omega) * cos(phi)]
    ])
    return R

def bounding_box_at_angle(alpha, geom):
    """Calculate the two equations of the bounding box at the given
    angle and its dimensions Dx and Dy. The equations describe lines
    that follow the sides of the bounding box."""
    if alpha != 90 and alpha != 270:
        a_ll = tan(alpha * pi / 180)

        if a_ll != 0:
            a_l_ = -1 / a_ll
        else:
            a_l_ = -1 / 0.000000000000000001

        x_centr = geom.centroid().asPoint().x()
        y_centr = geom.centroid().asPoint().y()
        b_ll = y_centr - a_ll * x_centr
        b_l_ = y_centr - a_l_ * x_centr

        A_ll = a_ll
        B_ll = -1
        C_ll = b_ll
        A_l_ = a_l_
        B_l_ = -1
        C_l_ = b_l_

        vrtx_dist_ll = []
        vrtx_dist_l_ = []

        for vertex in range(len(geom.convertToType(Qgis.GeometryType(1)).asPolyline())):
            vX = geom.vertexAt(vertex).x()
            vY = geom.vertexAt(vertex).y()
            d_ll = (A_ll * vX + B_ll * vY + C_ll) / sqrt(A_ll ** 2 + B_ll ** 2)
            vrtx_dist_ll.append(d_ll)
            d_l_ = (A_l_ * vX + B_l_ * vY + C_l_) / sqrt(A_l_ ** 2 + B_l_ ** 2)
            vrtx_dist_l_.append(d_l_)

        i1_ll = vrtx_dist_ll.index(max(vrtx_dist_ll))
        i2_ll = vrtx_dist_ll.index(min(vrtx_dist_ll))
        i1_l_ = vrtx_dist_l_.index(max(vrtx_dist_l_))
        i2_l_ = vrtx_dist_l_.index(min(vrtx_dist_l_))
        b1_ll = geom.vertexAt(i1_ll).y() - a_ll * geom.vertexAt(i1_ll).x()
        b2_ll = geom.vertexAt(i2_ll).y() - a_ll * geom.vertexAt(i2_ll).x()
        b1_l_ = geom.vertexAt(i1_l_).y() - a_l_ * geom.vertexAt(i1_l_).x()
        b2_l_ = geom.vertexAt(i2_l_).y() - a_l_ * geom.vertexAt(i2_l_).x()
        Dy = fabs(b1_ll - b2_ll) / sqrt(A_ll ** 2 + B_ll ** 2)
        Dx = fabs(b1_l_ - b2_l_) / sqrt(A_l_ ** 2 + B_l_ ** 2)

        if alpha > 90 and alpha < 270:
            b_ll = min(b1_ll, b2_ll)
        else:
            b_ll = max(b1_ll, b2_ll)
        if alpha >= 0 and alpha <= 180:
            b_l_ = min(b1_l_, b2_l_)
        else:
            b_l_ = max(b1_l_, b2_l_)
    else:
        x_max = geom.boundingBox().xMaximum()
        x_min = geom.boundingBox().xMinimum()
        y_max = geom.boundingBox().yMaximum()
        y_min = geom.boundingBox().yMinimum()

        Dx = y_max - y_min
        Dy = x_max - x_min
        if alpha == 270:
            a_ll, b_ll = line(y_max, y_min, x_max, x_max)
            a_l_, b_l_ = line(y_max, y_max, x_min, x_max)
        else:
            a_ll, b_ll = line(y_max, y_min, x_min, x_min)
            a_l_, b_l_ = line(y_min, y_min, x_min, x_max)
    return a_ll, b_ll, a_l_, b_l_, Dx, Dy