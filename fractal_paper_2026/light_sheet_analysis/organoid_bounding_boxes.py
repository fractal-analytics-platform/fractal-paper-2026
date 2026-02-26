from collections.abc import Sequence

import numpy as np
import polars as pl
from ngio import (
    OmeZarrContainer,
    Roi,
    open_ome_zarr_container,
)
from ngio.tables import RoiTable


def main():
    ZARR_PATH = "path/to/ome/zarr"
    TABLE_NAME = "organoid_bounding_boxes"
    TABLE_NAME_FULL_VIEWS = "organoid_frames"
    LEVEL = 3
    CHANNELS = None
    CHANNELS_MIN_MAX = (100, 1500)
    # T_IDXS = list(range(0, 666, 25)) # To generate a roi table on a subset of frames.
    T_IDXS = None
    OVERWRITE = True

    container = open_ome_zarr_container(ZARR_PATH)

    if TABLE_NAME in container.list_tables() and not OVERWRITE:
        print(f"{TABLE_NAME} exists already.")
    else:
        print("Computing rois...")
        roi_table = build_roi_table_with_otsu_thresholding(
            container,
            level=LEVEL,
            channels=CHANNELS,
            channels_min_max=CHANNELS_MIN_MAX,
            t_indices=T_IDXS,
            keep_n_largest=1,
        )

        print("Writing table...")
        container.add_table(name=TABLE_NAME, table=roi_table, overwrite=OVERWRITE)

        if TABLE_NAME_FULL_VIEWS is not None:
            full_view_df = build_default_organoid_roi_table(
                container
            ).lazy_frame.collect()
            full_view_tbl = _roi_table_from_polars(
                full_view_df.join(
                    roi_table.lazy_frame.collect(), on="FieldIndex", how="semi"
                )
            )
            container.add_table(
                name=TABLE_NAME_FULL_VIEWS, table=full_view_tbl, overwrite=OVERWRITE
            )


def build_roi_table_with_otsu_thresholding(
    container: OmeZarrContainer,
    level: int = 3,
    channels: Sequence[str] | None = None,
    channels_min_max: dict[str, tuple[float, float]]
    | tuple[float, float]
    | None = None,
    t_indices: Sequence[int] | None = None,
    keep_n_largest: int | None = None,
) -> RoiTable:
    """Build an organoid table using Otsu thresholding to define bounding boxes.

    Args:
        container: NGIO OmeZarrContainer to process.
        level: Level to process. Defaults to LEVEL.
        channels: Channels to process. Multiple channels are averaged before thresholding. Defaults to None meaning all channels.
        channels_min_max: Per channel minimum and maximum values for normalization. Defaults to None meaning raw values are used.
        t_indices: Time indices to process. Defaults to None meaning all timepoints.
        keep_n_largest: If specified, only keep the N largest objects per timepoint. Defaults to None meaning all objects are kept.

    Returns:
        ROI table with one entry per timepoint.
    """
    from skimage.exposure import rescale_intensity
    from skimage.filters import threshold_otsu
    from skimage.measure import label, regionprops_table

    img = container.get_image(str(level))
    if channels is None:
        channels = img.channel_labels

    if isinstance(channels_min_max, dict):
        for channel in channels:
            if channel not in channels_min_max:
                raise ValueError(
                    f"Channel {channel} not found in channels_min_max dictionary."
                )
    elif isinstance(channels_min_max, tuple):
        channels_min_max = {channel: channels_min_max for channel in channels}

    dask_arr = img.get_as_dask()
    pixel_size = img.dimensions.pixel_size

    if t_indices is None:
        t_indices = list(range(img.dimensions.get("t")))

    tbls = []
    for t_index in t_indices:
        print(f"Processing frame: {t_index}")
        frame = dask_arr[t_index].compute()

        # Normalize and average channels
        if img.is_multi_channels:
            norm_c_frames = []
            for channel in channels:
                c_frame = frame[img.get_channel_idx(channel)]
                if channels_min_max is not None:
                    norm_c_frames.append(
                        rescale_intensity(c_frame, in_range=channels_min_max[channel])
                    )
                else:
                    norm_c_frames.append(c_frame)
            frame = np.mean(np.stack(norm_c_frames, axis=0), axis=0)
        # Otsu thresholding and label
        thresh = threshold_otsu(frame)
        binary = frame > thresh
        label_image = label(binary)
        # Extract features
        props = regionprops_table(
            label_image,
            properties=["label", "bbox", "area"],
            spacing=pixel_size.zyx,
        )
        # Convert to RoiTable format
        if len(props["bbox-0"]) > 0:
            df = pl.DataFrame(props).with_columns(
                pl.lit(t_index).alias("t_index"),
                (pl.col("bbox-0") * pixel_size.get("z")).alias("z_micrometer"),
                (pl.col("bbox-1") * pixel_size.get("y")).alias("y_micrometer"),
                (pl.col("bbox-2") * pixel_size.get("x")).alias("x_micrometer"),
                ((pl.col("bbox-3") - pl.col("bbox-0")) * pixel_size.get("z")).alias(
                    "len_z_micrometer"
                ),
                ((pl.col("bbox-4") - pl.col("bbox-1")) * pixel_size.get("y")).alias(
                    "len_y_micrometer"
                ),
                ((pl.col("bbox-5") - pl.col("bbox-2")) * pixel_size.get("x")).alias(
                    "len_x_micrometer"
                ),
                pl.lit(t_index * pixel_size.get("t")).alias("t_second"),
                pl.lit(pixel_size.get("t")).alias("len_t_second"),
                pl.lit(f"t{t_index:04d}").alias("FieldIndex"),
            )
            tbls.append(df)
    out_tbl = pl.concat(tbls)

    if keep_n_largest is not None:
        out_tbl = (
            out_tbl.sort("area", descending=True)
            .group_by("t_index", maintain_order=True)
            .head(keep_n_largest)
        ).sort("t_second")
    return _roi_table_from_polars(out_tbl)


def build_default_organoid_roi_table(container: OmeZarrContainer) -> RoiTable:
    """Default roi table is the full frame at each timepoint."""

    table_defaults = (
        container.build_image_roi_table().lazy_frame.collect().to_dicts()[0]
    )
    img = container.get_image()
    dimensions = img.dimensions
    assert dimensions.is_3d, "Only 3D images are supported"
    assert dimensions.is_time_series, "Only time series images are supported"
    rows = []
    for i in range(dimensions.get("t")):
        rows.append(
            Roi.from_values(
                {
                    "x": (
                        table_defaults["x_micrometer"],
                        table_defaults["len_x_micrometer"],
                    ),
                    "y": (
                        table_defaults["y_micrometer"],
                        table_defaults["len_y_micrometer"],
                    ),
                    "z": (
                        table_defaults["z_micrometer"],
                        table_defaults["len_z_micrometer"],
                    ),
                    "t": (
                        i * dimensions.pixel_size.get("t"),
                        dimensions.pixel_size.get("t"),
                    ),
                },
                name=f"t{i:04d}",
            )
        )
    return RoiTable(rows)


def _roi_table_from_polars(
    df: pl.DataFrame, index_column: str = "FieldIndex"
) -> RoiTable:
    rois = []
    for row in df.iter_rows(named=True):
        rois.append(
            Roi.from_values(
                {
                    "x": (
                        row["x_micrometer"],
                        row["len_x_micrometer"],
                    ),
                    "y": (
                        row["y_micrometer"],
                        row["len_y_micrometer"],
                    ),
                    "z": (
                        row["z_micrometer"],
                        row["len_z_micrometer"],
                    ),
                    "t": (
                        row["t_second"],
                        row["len_t_second"],
                    ),
                },
                name=row[index_column],
            )
        )
    return RoiTable(rois)


if __name__ == "__main__":
    main()
