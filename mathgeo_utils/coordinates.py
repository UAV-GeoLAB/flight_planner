from math import (
    acos,
    cos,
    fabs,
    sin,
    sqrt,
)

def crs2pixel(geo, x, y):
    """Transform coordinates from CRS to pixel coordinates."""
    upx = geo[0]
    upy = geo[3]
    xscale = geo[1]
    yscale = geo[5]
    xskew = geo[2]
    yskew = geo[4]
    pc = sqrt(xscale ** 2 + yskew ** 2)
    pr = sqrt(yscale ** 2 + xskew ** 2)
    alpha = acos(xscale / pc)
    column = (cos(alpha) * (x - upx) + sin(alpha) * (y - upy)) / fabs(pc)
    row = (cos(alpha) * (upy - y) + sin(alpha) * (x - upx)) / fabs(pr)

    return column, row


def pixel2crs(geo, c, r):
    """Transform coordinates from pixel to CRS coordinates."""
    upx = geo[0]
    upy = geo[3]
    xscale = geo[1]
    yscale = geo[5]
    xskew = geo[2]
    yskew = geo[4]
    pc = sqrt(xscale ** 2 + yskew ** 2)
    pr = sqrt(yscale ** 2 + xskew ** 2)
    alpha = acos(xscale / pc)
    x = pc*cos(alpha)*c + pr*sin(alpha)*r + upx
    y = pc*sin(alpha)*c - pr*cos(alpha)*r + upy

    return x, y

def lines_intersection(a1, b1, a2, b2):
    """Calculate coordinates of intersection two lines."""
    x = (b2 - b1) / (a1 - a2)
    y = (b1 * a2 - b2 * a1) / (a2 - a1)
    return x, y

def line(ya, yb, xa, xb):
    """Calculate the coefficients a, b of the equation y = ax + b."""
    dy = ya - yb
    dx = xa - xb
    if dx != 0:
        a = dy / dx
        b = ya - (dy / dx) * xa
    else:
        a = dy / 0.000000000000000001
        b = ya - (dy / 0.000000000000000001) * xa
    return a, b

def transf_coord(transformer, x, y):
    """Transform coordinates between two CRS."""
    x_transformed, y_transformed = transformer.transform(x, y)
    return x_transformed, y_transformed