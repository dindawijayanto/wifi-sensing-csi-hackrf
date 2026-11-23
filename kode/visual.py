"""Grafik Case A: heatmap waktu x subcarrier |H[k]| per berkas, dan sebaran fitur per skenario.

Contoh:
    python kode/visual.py heatmap data/csi/*.csv
    python kode/visual.py fitur data/fitur.csv
"""
import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csi_core import AMP_COLS, SUBCARRIER  # noqa: E402


def heatmap(paths, keluar):
    os.makedirs(keluar, exist_ok=True)
    for p in paths:
        df = pd.read_csv(p)
        if df.empty:
            continue
        A = df[AMP_COLS].to_numpy()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                       gridspec_kw={"height_ratios": [3, 1]})
        im = ax1.pcolormesh(df["t_s"], SUBCARRIER, A.T, shading="nearest", cmap="viridis")
        ax1.set_ylabel("subcarrier k")
        ax1.set_title(f"|H[k]|  {os.path.basename(p)}")
        fig.colorbar(im, ax=[ax1, ax2], label="|H[k]|")
        ax2.plot(df["t_s"], df["rssi_dbfs"], ".", ms=2)
        ax2.set_ylabel("RSSI (dBFS)")
        ax2.set_xlabel("waktu (s)")
        out = os.path.join(keluar, "heatmap_" + os.path.splitext(os.path.basename(p))[0] + ".png")
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(out)


def sebaran_fitur(path, keluar):
    os.makedirs(keluar, exist_ok=True)
    df = pd.read_csv(path)
    label = sorted(df["label"].unique())
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    for ax, f, judul in [(axs[0], "csi_var_norm", "Variansi |H| ternormalisasi (CSI)"),
                         (axs[1], "rssi_var", "Variansi RSSI (dB^2)")]:
        ax.boxplot([df.loc[df["label"] == lb, f] for lb in label], tick_labels=label)
        ax.set_yscale("log")
        ax.set_title(judul)
        ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    out = os.path.join(keluar, "sebaran_fitur.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["heatmap", "fitur"])
    ap.add_argument("berkas", nargs="+")
    ap.add_argument("--keluar", default="hasil/grafik")
    a = ap.parse_args()
    paths = sorted({p for pola in a.berkas for p in glob.glob(pola)})
    if a.mode == "heatmap":
        heatmap(paths, a.keluar)
    else:
        sebaran_fitur(paths[0], a.keluar)


if __name__ == "__main__":
    main()
