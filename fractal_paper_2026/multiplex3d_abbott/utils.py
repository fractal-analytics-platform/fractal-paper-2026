
from typing import Optional, Literal, Sequence

import polars as pl

from ngio.common._roi import Roi
from ngio.hcs._plate import OmeZarrPlate

def _unnest_renaming_expression(df: pl.DataFrame, col: str, sep: str = "-") -> pl.Expr:
    return pl.col(col).struct.rename_fields(
        [f"{col}{sep}{f.name}" for f in df.schema.get(col).fields]
    )
    
    
def unnest_structs(
    df: pl.DataFrame, cols: str | Sequence[str], sep: str = "-"
) -> pl.DataFrame:
    if isinstance(cols, str):
        cols = (cols,)
    return df.select(
        [
            pl.exclude(cols),
            *[_unnest_renaming_expression(df, col, sep=sep) for col in cols],
        ]
    ).unnest(cols)


def unnest_all_structs(df: pl.DataFrame, sep: str = ".") -> pl.DataFrame:
    cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.Struct]
    return unnest_structs(df, cols, sep=sep)


def to_tall(
    df: pl.DataFrame,
    index_key: str,
):
    """Convert a polars DataFrame to a tall format."""
    # Get the columns to aggregate (excluding index_key)
    cols_to_agg = [col for col in df.columns if col != index_key]

    # Build expressions for each column: drop nulls and take the first value
    agg_exprs = [pl.col(c).drop_nulls().first().alias(c) for c in cols_to_agg]

    # Perform the groupby and aggregation
    result = df.group_by(index_key).agg(agg_exprs)
    result = result.with_columns(pl.col("label").cast(pl.Int32)).sort(by=index_key)
    return result

def get_ome_zarrs_filtered(ome_zarr_path_dict: dict, 
                           zarr_ending: str = "_registered"):
    """Filter ome-zarr path/container dict by zarr ending."""
    imgs_dict = {}
    for k, v in ome_zarr_path_dict.items():
        if k.endswith(zarr_ending):
            imgs_dict[k] = v
    return imgs_dict


def open_image_by_channel_label(ome_plate: OmeZarrPlate,
                                row: str,
                                column: str,
                                channel_label: str,
                                path: str = "0",
                                roi=Roi,
                                zarr_ending: Optional[str] = None,
                                masking_label_name: Optional[str] = None,
                                masking_table_name: Optional[str] = None, 
                                mode: Literal["numpy", "dask", "delayed"] = "numpy",
                                ):
    for acq in ome_plate.acquisition_ids:
        ome_zarr_dict = ome_plate.get_well_images(row=row, column=column, acquisition=acq)
        if zarr_ending is not None:
            ome_zarr_dict = get_ome_zarrs_filtered(ome_zarr_dict, zarr_ending=zarr_ending)
        if not len(ome_zarr_dict) == 1:
            return ValueError(f"Expected exactly one matching image for well {row}{column} "
                              f"and acquisition {acq}ß, but found {len(ome_zarr_dict)}.")
        ome_zarr = [*ome_zarr_dict.values()][0]
        channel_labels = ome_zarr.get_image(path=path).channel_labels
        if channel_label in channel_labels:
            c = channel_labels.index(channel_label)
            if masking_label_name is not None:
                imgs = ome_zarr.get_masked_image(masking_label_name=masking_label_name, 
                                                 masking_table_name=masking_table_name, path=path)
                img = imgs.get_roi_masked(label=int(roi.name), c=c, mode=mode)
            else:
                imgs = ome_zarr.get_image(path=path)
                img = imgs.get_roi(c=c, roi=roi, mode=mode)
            img = img.squeeze()
            return img