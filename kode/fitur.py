"""Fitur Case A: variansi |H[k]| per jendela dibandingkan variansi RSSI.

Langkah (case base 3.5): pilih pemancar target -> Hampel filter -> resampling ke grid
seragam -> fitur per jendela. Juga melaporkan laju paket aktual dan celah terpanjang.

Contoh:
    python kode/fitur.py data/csi/*.csv --rssi-min -40
    python kode/fitur.py data/csi/*.csv --cfo-min -5000 --cfo-max 5000 --jendela 1.0
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csi_core import AMP_COLS  # noqa: E402


def pilih_pemancar(df, rssi_min=None, rssi_max=None, cfo_min=None, cfo_max=None,
                   durasi_min=None, durasi_max=None):
    m = np.ones(len(df), bool)
    for kol, lo, hi in [("rssi_dbfs", rssi_min, rssi_max), ("cfo_hz", cfo_min, cfo_max),
                        ("durasi_us", durasi_min, durasi_max)]:
        if lo is not None:
            m &= df[kol].to_numpy() >= lo
        if hi is not None:
            m &= df[kol].to_numpy() <= hi
    return df[m].reset_index(drop=True)


def hampel(A, setengah=5, n_sigma=3.0):
    """Hampel filter per kolom. A: (n_paket, n_kolom). Outlier diganti median lokal."""
    d = pd.DataFrame(A)
    med = d.rolling(2 * setengah + 1, center=True, min_periods=1).median()
    mad = (d - med).abs().rolling(2 * setengah + 1, center=True, min_periods=1).median()
    out = (d - med).abs() > n_sigma * 1.4826 * mad
    return d.mask(out, med).to_numpy()


def resample(t, A, fs_grid):
    """Interpolasi linear (n_paket, 52) ke grid waktu seragam."""
    tg = np.arange(t[0], t[-1], 1.0 / fs_grid)
    Ag = np.column_stack([np.interp(tg, t, A[:, j]) for j in range(A.shape[1])])
    return tg, Ag


def fitur_berkas(df, jendela=1.0, fs_grid=50.0, min_paket=5):
    t = df["t_s"].to_numpy()
    A = hampel(df[AMP_COLS].to_numpy())
    tg, Ag = resample(t, A, fs_grid)
    rssi = df["rssi_dbfs"].to_numpy()
    hasil = []
    for w0 in np.arange(t[0], t[-1] - jendela + 1e-9, jendela):
        mp = (t >= w0) & (t < w0 + jendela)
        if mp.sum() < min_paket:
            continue
        mg = (tg >= w0) & (tg < w0 + jendela)
        Aw = Ag[mg]
        mu = Aw.mean(axis=0) + 1e-12
        hasil.append({
            "t_mulai": w0,
            "n_paket": int(mp.sum()),
            "csi_var": float(np.mean(Aw.var(axis=0))),                 # rata-rata var |H[k]|
            "csi_var_norm": float(np.mean(Aw.var(axis=0) / mu ** 2)),  # tak bergantung skala
            "rssi_var": float(np.var(rssi[mp])),                       # var RSSI (dB^2)
            "rssi_mean": float(np.mean(rssi[mp])),
        })
    return pd.DataFrame(hasil)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas", nargs="+", help="CSV hasil csi_ekstrak.py (boleh glob)")
    ap.add_argument("--keluar", default="data/fitur.csv")
    ap.add_argument("--laporan", default="hasil/tabel/laju_paket.csv")
    ap.add_argument("--jendela", type=float, default=1.0, help="panjang jendela (s)")
    ap.add_argument("--fs-grid", type=float, default=50.0, help="grid resampling (Hz)")
    ap.add_argument("--min-paket", type=int, default=5, help="paket minimum per jendela")
    for k in ["rssi-min", "rssi-max", "cfo-min", "cfo-max", "durasi-min", "durasi-max"]:
        ap.add_argument(f"--{k}", type=float, default=None)
    a = ap.parse_args()

    paths = sorted({p for pola in a.berkas for p in glob.glob(pola)})
    semua, laporan = [], []
    for p in paths:
        df = pd.read_csv(p)
        df = pilih_pemancar(df, a.rssi_min, a.rssi_max, a.cfo_min, a.cfo_max, a.durasi_min, a.durasi_max)
        nama = os.path.basename(p)
        if len(df) < 2:
            print(f"{nama}: kurang dari 2 paket setelah filter pemancar, dilewati")
            continue
        dur = df["t_s"].iloc[-1] - df["t_s"].iloc[0]
        laporan.append({"berkas": nama, "paket": len(df), "laju_paket_per_s": len(df) / max(dur, 1e-9),
                        "celah_maks_s": float(np.max(np.diff(df["t_s"])))})
        f = fitur_berkas(df, a.jendela, a.fs_grid, a.min_paket)
        f["berkas"] = nama
        for kol in ["label", "sesi", "subjek"]:
            f[kol] = df[kol].iloc[0] if kol in df else ""
        semua.append(f)
        print(f"{nama}: {len(df)} paket, {laporan[-1]['laju_paket_per_s']:.1f} paket/s, {len(f)} jendela")
    if not semua:
        sys.exit("Tidak ada fitur yang dihasilkan.")
    os.makedirs(os.path.dirname(a.keluar) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(a.laporan) or ".", exist_ok=True)
    pd.concat(semua, ignore_index=True).to_csv(a.keluar, index=False, float_format="%.6g")
    pd.DataFrame(laporan).to_csv(a.laporan, index=False, float_format="%.4g")
    print(f"Fitur -> {a.keluar}; laporan laju paket -> {a.laporan}")


if __name__ == "__main__":
    main()
