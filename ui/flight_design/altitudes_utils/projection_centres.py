from ....mathgeo.coordinates import lines_intersection

from math import (
    atan2,
    ceil,
    cos,
    fabs,
    pi,
    radians,
    sin,
    sqrt,

)

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)


def calculate_offsets(alpha, a_ll, b_ll, a_l_, b_l_, Dx, Dy, Bx, By, Ly, m, x):
    Nx, Ny = strips_projection_centres_number(Dx, Dy, Bx, By, Ly, m, x)
    Dy_o = max(Dy - 2 * (0.5 - x / 100) * Ly, 0)
    By_o = Dy_o / (Ny - 1) if Ny != 1 else 0

    A, B = a_ll, -1
    C1 = b_ll
    sign = 1 if alpha > 90 and alpha <= 270 else -1
    if Ny == 1:
        C2 = C1 + sign * Dy / 2 * sqrt(A**2 + B**2)
    else:
        C2 = C1 + sign * (0.5 - x / 100) * Ly * sqrt(A**2 + B**2)

    a1, b1 = a_ll, C2

    D = ((ceil(Dx / Bx)) * Bx - Dx) / 2
    A2, B2 = a_l_, -1
    C12 = b_l_
    sign2 = -1 if 0 <= alpha <= 180 else 1
    C22 = C12 + sign2 * D * sqrt(A2**2 + B2**2)
    a2, b2 = a_l_, C22

    x0, y0 = lines_intersection(a1, b1, a2, b2)
    dx = cos(radians(alpha)) * Bx
    dy = sin(radians(alpha)) * Bx
    dx0 = cos(radians(alpha) - pi / 2) * By_o
    dy0 = sin(radians(alpha) - pi / 2) * By_o

    return Nx, Ny, x0, y0, dx, dy, dx0, dy0


def create_layers(crs_vect):
    pc_layer = QgsVectorLayer(
        "Point?crs=" + str(crs_vect), "projection centres", "memory")
    pr = pc_layer.dataProvider()
    pr.addAttributes([
        QgsField("Strip", QVariant.String),
        QgsField("Photo Number", QVariant.String),
        QgsField("X [m]", QVariant.Double),
        QgsField("Y [m]", QVariant.Double),
        QgsField("Alt. ASL [m]", QVariant.Double),
        QgsField("Alt. AGL [m]", QVariant.Double),
        QgsField("Omega [deg]", QVariant.Double),
        QgsField("Phi [deg]", QVariant.Double),
        QgsField("Kappa [deg]", QVariant.Double)
    ])
    pc_layer.updateFields()

    photo_layer = QgsVectorLayer(
        "Polygon?crs=" + str(crs_vect), "photos", "memory")
    prov_photos = photo_layer.dataProvider()
    prov_photos.addAttributes([
        QgsField("Strip", QVariant.String),
        QgsField("Photo Number", QVariant.String)
    ])
    photo_layer.updateFields()

    return pc_layer, photo_layer


def create_strip_geometry(k, x0, y0, dx, dy, alpha, theta, d, Nx, m, geometry):
    xs1 = x0 + (-m) * dx + cos(radians(alpha) + theta - pi) * d
    ys1 = y0 + (-m) * dy + sin(radians(alpha) + theta - pi) * d
    xs2 = x0 + (-m) * dx + cos(radians(alpha) - theta + pi) * d
    ys2 = y0 + (-m) * dy + sin(radians(alpha) - theta + pi) * d
    xe3 = x0 + (Nx - m - 1) * dx + cos(radians(alpha) + theta) * d
    ye3 = y0 + (Nx - m - 1) * dy + sin(radians(alpha) + theta) * d
    xe4 = x0 + (Nx - m - 1) * dx + cos(radians(alpha) - theta) * d
    ye4 = y0 + (Nx - m - 1) * dy + sin(radians(alpha) - theta) * d
    strip_pnts = [QgsPointXY(xs1, ys1), QgsPointXY(xs2, ys2),
                  QgsPointXY(xe3, ye3), QgsPointXY(xe4, ye4)]
    geom_strip = QgsGeometry.fromPolygonXY([strip_pnts])
    return geom_strip.intersection(geometry)


def compute_photo_geometry(xi, yi, alpha, theta, d, Ly):
    x1 = xi + cos(radians(alpha) + theta - pi) * d
    y1 = yi + sin(radians(alpha) + theta - pi) * d
    x2 = xi + cos(radians(alpha) - theta + pi) * d
    y2 = yi + sin(radians(alpha) - theta + pi) * d
    x3 = xi + cos(radians(alpha) + theta) * d
    y3 = yi + sin(radians(alpha) + theta) * d
    x4 = xi + cos(radians(alpha) - theta) * d
    y4 = yi + sin(radians(alpha) - theta) * d
    geom_poly = QgsGeometry.fromPolygonXY([
        [QgsPointXY(x1, y1), QgsPointXY(x2, y2),
         QgsPointXY(x3, y3), QgsPointXY(x4, y4)]
    ])
    xp = xi + cos(radians(alpha) + pi / 2) * Ly / 2
    yp = yi + sin(radians(alpha) + pi / 2) * Ly / 2
    xk = xi + cos(radians(alpha) - pi / 2) * Ly / 2
    yk = yi + sin(radians(alpha) - pi / 2) * Ly / 2
    central_line = QgsGeometry.fromPolylineXY(
        [QgsPointXY(xp, yp), QgsPointXY(xk, yk)])
    return geom_poly, central_line


def add_photo_feature(pr, prov_photos, pc_layer, photo_layer, xi, yi, H, kappa, s_nr, p_nr, geom_poly):
    feat_pnt = QgsFeature()
    pnt = QgsPointXY(xi, yi)
    feat_pnt.setGeometry(QgsGeometry.fromPointXY(pnt))
    feat_pnt.setAttributes([s_nr, p_nr, round(xi, 2), round(
        yi, 2), round(H, 2), None, 0, 0, kappa])
    pr.addFeature(feat_pnt)
    pc_layer.updateExtents()

    feat_poly = QgsFeature()
    feat_poly.setGeometry(geom_poly)
    feat_poly.setAttributes([s_nr, p_nr])
    prov_photos.addFeature(feat_poly)
    photo_layer.updateExtents()


def projection_centres(alpha, geometry, crs_vect, a_ll, b_ll, a_l_, b_l_,
                       Dx, Dy, Bx, By, Lx, Ly, x, m, H, strip_nr, photo_nr):

    Nx, Ny, x0, y0, dx, dy, dx0, dy0 = calculate_offsets(
        alpha, a_ll, b_ll, a_l_, b_l_, Dx, Dy, Bx, By, Ly, m, x
    )
    pc_layer, photo_layer = create_layers(crs_vect)
    d = sqrt((Lx / 2)**2 + (Ly / 2)**2)
    theta = fabs(atan2(Ly / 2, Lx / 2))

    for k in range(Ny):
        geom_strip = create_strip_geometry(
            k, x0, y0, dx, dy, alpha, theta, d, Nx, m, geometry)
        kappa = (alpha + 180) % 360 if k % 2 != 0 else alpha
        n_prev = -m - 1

        for n in range(-m, Nx - m):
            xi = x0 + n * dx
            yi = y0 + n * dy
            geom_poly, central_line = compute_photo_geometry(
                xi, yi, alpha, theta, d, Ly)

            if central_line.distance(geom_strip) <= m * Bx:
                photo_nr += 1
                if fabs(n - n_prev) != 1:
                    strip_nr += 1
                s_nr = f"{strip_nr:04d}"
                p_nr = f"{photo_nr:05d}"
                add_photo_feature(pc_layer.dataProvider(), photo_layer.dataProvider(),
                                  pc_layer, photo_layer, xi, yi, H, kappa, s_nr, p_nr, geom_poly)
                n_prev = n

        if k % 2 == 0:
            first_p = int(p_nr) + 1
            first_s = int(s_nr) + 1
        else:
            update_order(k, first_p, first_s, p_nr, s_nr, pc_layer)

        x0 += dx0
        y0 += dy0

    return pc_layer, photo_layer, strip_nr, photo_nr


def strips_projection_centres_number(Dx, Dy, Bx, By, Ly, m, x):
    """Return number of strips Ny and projection centres Nx
    for Area of Interst or one segment of corridor flight."""

    Dy_o = Dy - 2 * (0.5 - x / 100) * Ly

    if Dy_o < 0:
        Dy_o = 0
    Ny = ceil(Dy_o / By) + 1

    Nx = ceil(Dx / Bx) + 2 * m + 1

    return Nx, Ny


def update_order(k, first_p, first_s, p_nr, s_nr, pc_layer):
    """Update order of elements in layer"""
    list_p = list(range(first_p, int(p_nr) + 1))
    list_s = list(range(first_s, int(s_nr) + 1))
    i = len(list_p) - 1
    j = len(list_s) - 1
    nr_strp_prev = list_s[0]
    for f in pc_layer.getFeatures():
        nr_zdj = int(f.attribute('Photo Number'))
        nr_strp = int(f.attribute('Strip'))

        if nr_zdj in list_p:
            p_nr = '%(p_nr)05d' % {'p_nr': list_p[i]}
            i -= 1
            if nr_strp != nr_strp_prev:
                j -= 1

            s_nr = '%(s_nr)04d' % {'s_nr': list_s[j]}
            pc_layer.startEditing()
            pc_layer.changeAttributeValue(f.id(), 1, p_nr)
            pc_layer.changeAttributeValue(f.id(), 0, s_nr)
            pc_layer.commitChanges()

            nr_strp_prev = nr_strp
