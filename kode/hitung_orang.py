"""Eksplorasi cadangan Case A: apakah fitur CSI naik monoton dengan jumlah orang bergerak?

Masukan: CSV hasil fitur.py yang berisi label untuk 0, 1, 2, 3 orang. Peta label ke jumlah
orang diberikan dengan --peta. Keluaran: median fitur per jumlah orang, korelasi Spearman,
cek monoton, dan boxplot.

Contoh:
    python kode/fitur.py data/csi/A_s1_*.csv data/csi/A_e1_G*.csv --cfo-min ... --keluar data/fitur_orang.csv
    python kode/hitung_orang.py data/fitur_orang.csv --peta kosong=0 jalan_los=1 jalan_2orang=2 jalan_3orang=3
"""
import argparse
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas_fitur", metavar="fitur.csv")
    ap.add_argument("--peta", nargs="+", required=True, help="label=jumlah_orang")
    ap.add_argument("--fitur", nargs="+", default=["csi_var_norm", "rssi_var"])
    ap.add_argument("--keluar", default="hasil/tabel/hitung_orang.csv")
    ap.add_argument("--gambar", default="hasil/grafik/hitung_orang.png")
    a = ap.parse_args()

    peta = {k: int(v) for k, v in (s.split("=") for s in a.peta)}
    df = pd.read_csv(a.berkas_fitur)
    df = df[df["label"].isin(peta)].copy()
    df["orang"] = df["label"].map(peta)
    if df["orang"].nunique() < 3:
        raise SystemExit(f"Butuh minimal 3 jumlah orang berbeda, ada: {sorted(df['orang'].unique())}")

    baris = []
    for kol in a.fitur:
        med = df.groupby("orang")[kol].median()
        rho, p = spearmanr(df["orang"], df[kol])
        monoton = bool(np.all(np.diff(med.to_numpy()) > 0))
        baris.append({"fitur": kol, "spearman_rho": rho, "p": p, "monoton": monoton,
                      **{f"median_{n}_orang": v for n, v in med.items()}})
        print(f"{kol}: median per jumlah orang { {int(k): round(float(v), 5) for k, v in med.items()} }, "
              f"Spearman rho {rho:.3f} (p={p:.2g}), monoton naik: {'YA' if monoton else 'TIDAK'}")
    os.makedirs(os.path.dirname(a.keluar) or ".", exist_ok=True)
    pd.DataFrame(baris).to_csv(a.keluar, index=False, float_format="%.4g")
    print(f"Tabel -> {a.keluar}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    n = sorted(df["orang"].unique())
    fig, axs = plt.subplots(1, len(a.fitur), figsize=(5.5 * len(a.fitur), 4))
    for ax, kol in zip(np.atleast_1d(axs), a.fitur):
        ax.boxplot([df.loc[df["orang"] == k, kol] for k in n], tick_labels=[str(k) for k in n])
        ax.set_yscale("log")
        ax.set_xlabel("jumlah orang bergerak")
        ax.set_title(kol)
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.gambar) or ".", exist_ok=True)
    fig.savefig(a.gambar, dpi=130)
    print(f"Grafik -> {a.gambar}")


if __name__ == "__main__":
    main()
