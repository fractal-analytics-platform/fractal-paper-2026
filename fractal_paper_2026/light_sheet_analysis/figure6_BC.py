from pathlib import Path

import imageio.v3 as iio
import napari
import polars as pl
from napari.settings import get_settings
from ngio import open_ome_zarr_container
from ngio.tables import RoiTable
from organoid_bounding_boxes import _roi_table_from_polars

SPATIAL_DIMS = ["z", "y", "x"]


def main():
    ZARR_PATH = r"W:\scratch\gliberal\Users\hessmax\fractal\497_light_sheet_data_processing\2462_ls1_002\data.zarr"
    OUTPUT = "../../output"
    TABLE_NAME = "organoid_bounding_boxes"
    LEVEL = 1
    SHIFT = 0.0
    PADDING = 5.0
    LABEL_NAME = "nuclei_sam"
    EVERY_NTH = 50
    CROP_PERC_2D = 0.36  # 0.3 for EVERY_NTH=100
    CROP_PERC_3D = 0.3  # 0.2 for EVERY_NTH=100, 0.05 for EVERY_NTH=200
    IS_2D = False  # Script ran twice, for 2D and 3D

    settings = get_settings()
    settings.application.window_fullscreen = True
    settings.appearance.theme = "dark"

    container = open_ome_zarr_container(ZARR_PATH)
    print("Loading table...")
    _tbl_rois = container.get_table(TABLE_NAME)
    tbl_rois = RoiTable(_tbl_rois.rois()[::EVERY_NTH])
    df_rois = tbl_rois.lazy_frame.collect()

    df_rois = df_rois.with_columns(
        pl.col.x_micrometer - PADDING,
        pl.col.len_x_micrometer + PADDING,
        pl.col.y_micrometer - PADDING,
        pl.col.len_y_micrometer + PADDING,
    )

    tbl_rois = _roi_table_from_polars(df_rois)
    x_offsets = df_rois.select(
        ((pl.col("len_x_micrometer") + SHIFT).shift(1, fill_value=0.0)).cum_sum()
    ).to_series()
    y_offsets = df_rois.select((pl.col("len_y_micrometer") / 2) * -1).to_series()
    z_offsets = df_rois.select((pl.col("len_z_micrometer") / 2) * -1).to_series()

    print("Loading images...")
    img = container.get_image(str(LEVEL))
    lbl_img = container.get_label(LABEL_NAME, path=str(LEVEL))
    arrs = [img.get_roi(roi) for roi in tbl_rois.rois()]
    lbls = [lbl_img.get_roi(roi) for roi in tbl_rois.rois()]
    pixel_size = img.dimensions.pixel_size

    if IS_2D:
        print("Visualize 2D in napari...")
        viewer = napari.Viewer(show=True)
        for arr, lbl, x_off, y_off in zip(arrs, lbls, x_offsets, y_offsets):
            translate = (y_off, x_off)
            viewer.add_image(
                # arr.max(axis=2),
                arr[:, :, arr.shape[2] // 2, :, :],
                channel_axis=1,
                scale=pixel_size.yx,
                contrast_limits=[100, 1000],
                blending="additive",
                translate=translate,
            )
            viewer.add_labels(
                # arr.max(axis=2),
                lbl[:, lbl.shape[1] // 2, :, :],
                scale=pixel_size.yx,
                translate=translate,
            )
        viewer.reset_view()

        # 2D screenshot with labels
        screenshot_2d_labels_path = (
            Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_2d_with_labels.png"
        )
        if screenshot_2d_labels_path.exists():
            screenshot_2d_labels_path.unlink()

        screenshot_2d_labels = viewer.screenshot(screenshot_2d_labels_path)

        crop = int(screenshot_2d_labels.shape[0] * CROP_PERC_2D)
        iio.imwrite(
            screenshot_2d_labels_path.parent
            / f"{screenshot_2d_labels_path.stem}_crp.png",
            screenshot_2d_labels[crop:-crop, :, :],
        )

        # 2D screenshot without labels
        for layer in viewer.layers:
            if layer._type_string == "labels":
                layer.visible = False

        screenshot_2d_path = Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_2d.png"
        if screenshot_2d_path.exists():
            screenshot_2d_path.unlink()
        screenshot_2d = viewer.screenshot(screenshot_2d_path)

        iio.imwrite(
            screenshot_2d_path.parent / f"{screenshot_2d_path.stem}_crp.png",
            screenshot_2d[crop:-crop, :, :],
        )
        # viewer.show(block=True)
    else:
        print("Visualize 3D in napari...")
        viewer = napari.Viewer(ndisplay=3)
        for arr, lbl, x_off, y_off, z_off in zip(
            arrs, lbls, x_offsets, y_offsets, z_offsets
        ):
            translate = (z_off, y_off, x_off)
            viewer.add_image(
                # arr.max(axis=2),
                arr,
                channel_axis=1,
                scale=pixel_size.zyx,
                contrast_limits=([100, 600], [100, 700]),
                blending="additive",
                rendering="attenuated_mip",
                translate=translate,
            )
            viewer.add_labels(
                # arr.max(axis=2),
                lbl,
                scale=pixel_size.zyx,
                translate=translate,
            )
        viewer.reset_view()

        viewer.camera.angles = (
            1.1064776820448703,
            1.0506906368916895,
            -32.54626922488174,
        )
        # 3D screenshots with labels
        screenshot_3d_labels_path = (
            Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_3d_with_labels.png"
        )
        if screenshot_3d_labels_path.exists():
            screenshot_3d_labels_path.unlink()

        screenshot_3d_labels = viewer.screenshot(screenshot_3d_labels_path.as_posix())

        crop_3d = int(screenshot_3d_labels.shape[0] * CROP_PERC_3D)
        iio.imwrite(
            screenshot_3d_labels_path.parent
            / f"{screenshot_3d_labels_path.stem}_crp.png",
            screenshot_3d_labels[crop_3d:-crop_3d, :, :],
        )

        # 3D screenshots without labels
        for layer in viewer.layers:
            if layer._type_string == "labels":
                layer.visible = False
        screenshot_3d_path = Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_3d.png"
        if screenshot_3d_path.exists():
            screenshot_3d_path.unlink()

        screenshot_3d = viewer.screenshot(screenshot_3d_path.as_posix())

        iio.imwrite(
            screenshot_3d_path.parent / f"{screenshot_3d_path.stem}_crp.png",
            screenshot_3d[crop_3d:-crop_3d, :, :],
        )

        # 3D screenshots labels only
        for layer in viewer.layers:
            if layer._type_string == "labels":
                layer.visible = True
                layer.opacity = 1.0
            elif layer._type_string == "image":
                layer.visible = False
        screenshot_3d_only_labels_path = (
            Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_3d_only_labels.png"
        )
        if screenshot_3d_only_labels_path.exists():
            screenshot_3d_only_labels_path.unlink()

        screenshot_3d_only_labels = viewer.screenshot(
            screenshot_3d_only_labels_path.as_posix()
        )

        iio.imwrite(
            screenshot_3d_only_labels_path.parent
            / f"{screenshot_3d_only_labels_path.stem}_crp.png",
            screenshot_3d_only_labels[crop_3d:-crop_3d, :, :],
        )

        # 3D screenshots labels only white background
        for layer in viewer.layers:
            if layer._type_string == "labels":
                layer.visible = True
                layer.opacity = 1.0
            elif layer._type_string == "image":
                layer.visible = False

        settings.appearance.theme = "light"
        screenshot_3d_only_labels_path = (
            Path(OUTPUT) / f"n{len(df_rois):02d}_timecourse_3d_only_labels_wbg.png"
        )
        if screenshot_3d_only_labels_path.exists():
            screenshot_3d_only_labels_path.unlink()

        screenshot_3d_only_labels = viewer.screenshot(
            screenshot_3d_only_labels_path.as_posix()
        )

        iio.imwrite(
            screenshot_3d_only_labels_path.parent
            / f"{screenshot_3d_only_labels_path.stem}_crp.png",
            screenshot_3d_only_labels[crop_3d:-crop_3d, :, :],
        )
        # viewer.show(block=True)


if __name__ == "__main__":
    main()
