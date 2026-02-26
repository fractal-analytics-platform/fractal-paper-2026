from pathlib import Path

import matplotlib.pyplot as plt
import ngio
import numpy as np
import polars as pl
import seaborn as sns


def main():
    ZARR_PATH = "path/to/ome/zarr"
    EVERY_NTH = 50
    OUTPUT_PATH = "fractal_paper_2026/light_sheet_analysis/figs"
    Path(OUTPUT_PATH).mkdir(exist_ok=True)

    container = ngio.open_ome_zarr_container(ZARR_PATH)
    df_rois = (
        container.get_table("organoid_bounding_boxes")
        .lazy_frame.collect()
        .with_row_index("t_id")
        .with_columns((pl.col("t_id") * 600 / 60 / 60).alias("t_hour"))
    )

    df_nucs = (
        container.get_table("region_props_features")
        .lazy_frame.collect()
        .with_columns(
            (pl.col("time") * 600 / 60 / 60).alias("t_hour"),
            (pl.col("time").cast(pl.UInt32)).alias("t_id"),
        )
    )

    fig, ax = plt.subplots(figsize=(3.5, 2.6), dpi=300)
    sns.scatterplot(
        df_nucs.with_columns(
            pl.col("area") * np.prod(container.get_image().pixel_size.zyx)
        )
        .filter(pl.col("area") < 2000)
        .filter(stratified_sample(by="t_id", n=32, seed=42)),
        x="t_hour",
        y="area",
        s=3,
        alpha=0.15,
    )
    ax.set_xlabel("Time [h]")
    ax.set_ylabel("Nuclear Volume [µm³]")
    for row in df_rois[::EVERY_NTH].iter_rows(named=True):
        ax.axvline(row["t_hour"], color="0.5", lw=0.7, ls="dotted")
    plt.tight_layout()
    fig.savefig(str(Path(OUTPUT_PATH) / "panelA.png"))

    fig, ax = plt.subplots(figsize=(3.5, 2.6), dpi=300)
    sns.scatterplot(
        df_nucs.with_columns(
            pl.col("area") * np.prod(container.get_image().pixel_size.zyx)
        ).filter(pl.col("area") < 2000),
        x="t_hour",
        y="area",
        s=3,
        alpha=0.15,
    )
    ax.set_xlabel("Time [h]")
    ax.set_ylabel("Nuclear Volume [µm³]")
    for row in df_rois[::EVERY_NTH].iter_rows(named=True):
        ax.axvline(row["t_hour"], color="0.5", lw=0.7, ls="dotted")
    plt.tight_layout()
    fig.savefig(str(Path(OUTPUT_PATH) / "panelA_supplementary.png"))

    fig, ax = plt.subplots(figsize=(3.5, 2.6), dpi=300)
    sns.scatterplot(
        df_nucs.group_by("t_id")
        .agg(pl.len().alias("count"), pl.col("t_hour").first())
        .with_columns(pl.col("count").log(base=2).alias("log2_count")),
        x="t_hour",
        y="count",
        s=3,
        alpha=0.8,
    )
    ax.set_xlabel("Time [h]")
    ax.set_ylabel("Nucleus Count")
    for row in df_rois[::EVERY_NTH].iter_rows(named=True):
        ax.axvline(row["t_hour"], color="0.5", lw=0.7, ls="dotted")

    plt.tight_layout()
    fig.savefig(str(Path(OUTPUT_PATH) / "panelB.png"))


def stratified_sample(by: str, n: int, seed: int | None = None) -> pl.Expr:
    return pl.int_range(0, pl.len()).shuffle(seed).over(by) < n


if __name__ == "__main__":
    main()
