import numpy as np
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsPointXY,
    QgsGeometry,
    QgsCoordinateReferenceSystem
)
from .....functions import (
    rotation_matrix,
    transf_coord,
    crs2pixel,
    image_edge_points,
    ground_edge_points,
    change_layer_style,
    overlap_photo,
    gsd
)
from .utils import clip_raster
from .styles import footprint_props
from scipy import ndimage

def process_footprints(worker):
    transf_vct_rst = transf_rst_vct = None
    if worker.crs_rst != worker.crs_vct:
        from pyproj import Transformer
        transf_vct_rst = Transformer.from_crs(worker.crs_vct, worker.crs_rst, always_xy=True)
        transf_rst_vct = Transformer.from_crs(worker.crs_rst, worker.crs_vct, always_xy=True)

    Z_srtm = worker.raster.GetRasterBand(1).ReadAsArray()
    nodata = worker.raster.GetRasterBand(1).GetNoDataValue()
    rst_array = np.ma.masked_equal(Z_srtm, nodata)
    Z_min = np.nanmin(rst_array)

    uplx_r, xres_r, xskew_r, uply_r, yskew_r, yres_r = worker.raster.GetGeoTransform()

    if QgsCoordinateReferenceSystem(worker.crs_rst).isGeographic():
        uplx_v, uply_v = transf_coord(transf_rst_vct, uplx_r, uply_r)
        uplx_v_n, uply_v_n = transf_coord(transf_rst_vct, uplx_r + xres_r, uply_r + yres_r)
        xres_r = abs(uplx_v_n - uplx_v)
        yres_r = abs(uply_v_n - uply_v)

    mean_res = (abs(xres_r) + abs(yres_r)) / 2

    layer = worker.layer
    footprint_lay = QgsVectorLayer("Polygon?crs=EPSG:2180", "footprints", "memory")
    provider = footprint_lay.dataProvider()

    features = layer.getFeatures()
    xyf_corners = worker.camera.image_corners()

    feat_footprint = QgsFeature()
    ds_list, ulx_list, uly_list, lrx_list, lry_list = [], [], [], [], []

    feat_count = layer.featureCount()
    progress_c = 0
    step = feat_count // 1000 if feat_count >= 1000 else 1

    for feature in features:
        if worker.killed:
            worker.handle_cancel()
            return None

        Xs = feature.geometry().asPoint().x()
        Ys = feature.geometry().asPoint().y()
        Zs = feature.attribute(worker.height_f)

        if not worker.height_is_ASL:
            x, y = Xs, Ys
            if worker.crs_rst != worker.crs_vct:
                x, y = transf_coord(transf_vct_rst, Xs, Ys)
            terrain_height, _ = worker.DTM.dataProvider().sample(QgsPointXY(x, y), 1)
            Zs += terrain_height

        omega = feature.attribute(worker.omega_f)
        phi = feature.attribute(worker.phi_f)
        kappa = feature.attribute(worker.kappa_f)
        R = rotation_matrix(omega, phi, kappa)

        clipped_DTM, clipped_geot = clip_raster(worker.raster, xyf_corners, R, Xs, Ys, Zs, Z_min,
                                                transf_vct_rst, worker.crs_rst, worker.crs_vct)

        if worker.crs_rst != worker.crs_vct:
            Xs_rast, Ys_rast = transf_coord(transf_vct_rst, Xs, Ys)
            c, r = crs2pixel(clipped_geot, Xs_rast, Ys_rast)
        else:
            c, r = crs2pixel(clipped_geot, Xs, Ys)

        Z_under_pc = ndimage.map_coordinates(clipped_DTM, np.array([[r, c]]).T)[0]

        xyf = image_edge_points(worker.camera, Z_under_pc, Zs, mean_res)
        footprint_vertices = ground_edge_points(R, Z_under_pc, worker.threshold, xyf,
                                                Xs, Ys, Zs, clipped_DTM, clipped_geot,
                                                worker.crs_rst, worker.crs_vct, transf_vct_rst)

        geom_footprint = QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in footprint_vertices]])
        feat_footprint.setGeometry(geom_footprint)
        provider.addFeatures([feat_footprint])
        footprint_lay.updateExtents()

        if worker.overlap_bool or worker.gsd_bool:
            if worker.crs_vct != worker.crs_rst:
                X_rast, Y_rast = transf_coord(transf_vct_rst, footprint_vertices[:, 0], footprint_vertices[:, 1])
                footprint_vertices = np.hstack((X_rast.reshape((-1, 1)), Y_rast.reshape((-1, 1))))

            overlap_arr, overlap_geot = overlap_photo(footprint_vertices, clipped_geot, clipped_DTM.shape)

            deltac = int(abs(round((clipped_geot[0] - overlap_geot[0]) / overlap_geot[1])))
            deltar = int(abs(round((clipped_geot[3] - overlap_geot[3]) / overlap_geot[5])))
            fitted_DTM = clipped_DTM[deltar:overlap_arr.shape[0]+deltar, deltac:overlap_arr.shape[1]+deltac]

            projection_center = np.array([[Xs], [Ys], [Zs]])
            img_coords = np.array([[0], [0], [-worker.camera.focal_length]])
            image_crs = projection_center + np.dot(R, img_coords)
            X, Y, Z = image_crs.flatten()


            gsd_array = gsd(fitted_DTM, overlap_geot, Xs, Ys, Zs, X, Y, Z, worker.camera.focal_length, worker.camera.sensor_size)

            gsd_masked = np.where(gsd_array * overlap_arr == 0, 1000, gsd_array * overlap_arr)
            ds_list.append([gsd_masked, overlap_arr, overlap_geot])

            upx, xres, xskew, upy, yskew, yres = overlap_geot
            cols, rows = overlap_arr.shape[1], overlap_arr.shape[0]
            ulx = upx
            uly = upy
            lrx = upx + cols * xres + rows * xskew
            lry = upy + cols * yskew + rows * yres
            ulx_list.append(ulx)
            uly_list.append(uly)
            lrx_list.append(lrx)
            lry_list.append(lry)

        progress_c += 1
        if progress_c % step == 0:
            worker.progress.emit(int(progress_c / feat_count * 100))

        if worker.footprint_bool:
            change_layer_style(footprint_lay, footprint_props)

    return footprint_lay, ds_list, ulx_list, uly_list, lrx_list, lry_list, xres, yres
