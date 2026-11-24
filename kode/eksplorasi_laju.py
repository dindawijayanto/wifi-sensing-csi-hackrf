"""Eksplorasi Case A: batas laju paket untuk deteksi kosong vs bergerak.

Data CSI hotspot (12 rekaman sesi) ditipiskan ke laju tertentu (default 50/20/10/5 paket/s)
dengan grid waktu teratur, meniru beacon yang dikirim pada interval tetap. Untuk tiap laju,
fitur per jendela dihitung ulang lalu detektor ambang dievaluasi leave-one-session-out
(cara yang sama dengan klasifikasi.py). Keluaran: tabel akurasi/FPR/FNR per laju, grafik
akurasi vs laju, dan laju terendah yang masih memberi akurasi >= 90%.

Contoh:
    python kode/eksplorasi_laju.py "data/csi/*.csv" --cfo-min -15000 --cfo-max -9000
    python kode/eksplorasi_laju.py "data/csi/*.csv" --laju 50 30 20 15 10 7 5 --ulang 5
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitur import pilih_pemancar, fitur_berkas  # noqa: E402
from klasifikasi import pilih_ambang, metrik  # noqa: E402

LAJU_BEACON = 9.77   # paket/s, beacon AP (interval 102.4 ms)
LAJU_CASE_A = 20.0
TARGET_AKURASI = 0.90


def tipiskan(df, laju, fase=0.0):
    """Ambil paket pertama pada atau setelah setiap detak grid 1/laju."""
    t = df["t_s"].to_numpy()
    grid = np.arange(t[0] + fase, t[-1], 1.0 / laju)
    idx = np.unique(np.searchsorted(t, grid))
    idx = idx[idx < len(t)]
    return df.iloc[idx].reset_index(drop=True)


def loso(F, kolom, kosong, bergerak):
    F = F[F["label"].isin(kosong + bergerak)].copy()
    F["y"] = F["label"].isin(bergerak).astype(int)
    hasil = []
    for s in sorted(F["sesi"].astype(str).unique()):
        latih, uji = F[F["sesi"].astype(str) != s], F[F["sesi"].astype(str) == s]
        if latih["y"].nunique() < 2 or uji.empty:
            continue
        th = pilih_ambang(latih[kolom].to_numpy(), latih["y"].to_numpy())
        hasil.append(metrik(uji[kolom].to_numpy() > th, uji["y"].to_numpy()))
    return pd.DataFrame(hasil)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas", nargs="+", help="CSV hasil csi_ekstrak.py (boleh glob)")
    ap.add_argument("--laju", nargs="+", type=float, default=[50, 20, 10, 5], help="laju target (paket/s)")
    ap.add_argument("--ulang", type=int, default=3, help="jumlah fase grid berbeda yang dirata-rata")
    ap.add_argument("--fitur", nargs="+", default=["csi_var_norm", "rssi_var"])
    ap.add_argument("--kosong", nargs="+", default=["kosong"])
    ap.add_argument("--bergerak", nargs="+", default=["jalan_los", "jalan_luar"])
    ap.add_argument("--jendela", type=float, default=1.0)
    ap.add_argument("--fs-grid", type=float, default=50.0)
    ap.add_argument("--min-paket", type=int, default=5, help="paket minimum per jendela pada laju asli")
    for k in ["rssi-min", "rssi-max", "cfo-min", "cfo-max", "durasi-min", "durasi-max"]:
        ap.add_argument(f"--{k}", type=float, default=None)
    ap.add_argument("--keluar", default="hasil/tabel/eksplorasi_laju.csv")
    ap.add_argument("--gambar", default="hasil/grafik/eksplorasi_laju.png")
    a = ap.parse_args()

    paths = sorted({p for pola in a.berkas for p in glob.glob(pola)})
    data = []
    for p in paths:
        df = pd.read_csv(p, dtype={"sesi": str})
        df = pilih_pemancar(df, a.rssi_min, a.rssi_max, a.cfo_min, a.cfo_max, a.durasi_min, a.durasi_max)
        if len(df) >= 2 and df["label"].iloc[0] in a.kosong + a.bergerak:
            data.append(df)
    if not data:
        sys.exit("Tidak ada CSV dengan label kosong/bergerak setelah filter pemancar.")
    laju_asli = np.median([len(d) / (d["t_s"].iloc[-1] - d["t_s"].iloc[0]) for d in data])
    print(f"{len(data)} berkas, laju asli median {laju_asli:.1f} paket/s")

    baris = []
    for r in ["asli"] + sorted(a.laju, reverse=True):
        fase_list = [0.0] if r == "asli" else np.arange(a.ulang) / a.ulang / r
        min_p = a.min_paket if r == "asli" else max(2, min(a.min_paket, int(0.6 * r * a.jendela)))
        for fase in fase_list:
            semua, laju_nyata = [], []
            for df in data:
                d = df if r == "asli" else tipiskan(df, r, fase)
                if len(d) < 2:
                    continue
                laju_nyata.append(len(d) / (d["t_s"].iloc[-1] - d["t_s"].iloc[0]))
                f = fitur_berkas(d, a.jendela, a.fs_grid, min_p)
                if f.empty:
                    continue
                f["label"], f["sesi"] = d["label"].iloc[0], str(d["sesi"].iloc[0])
                semua.append(f)
            if not semua:
                continue
            F = pd.concat(semua, ignore_index=True)
            for kol in a.fitur:
                m = loso(F, kol, a.kosong, a.bergerak)
                if m.empty:
                    continue
                baris.append({"laju_target": r, "laju_nyata": float(np.median(laju_nyata)), "fitur": kol,
                              "fase": fase, "akurasi": m["akurasi"].mean(), "fpr": m["fpr"].mean(),
                              "fnr": m["fnr"].mean(), "n_fold": len(m)})
    if not baris:
        sys.exit("Tidak ada hasil. Butuh minimal 2 sesi berisi kosong dan bergerak.")

    H = pd.DataFrame(baris)
    R = (H.groupby(["fitur", "laju_target"], sort=False)
          [["laju_nyata", "akurasi", "fpr", "fnr"]].mean().reset_index())
    os.makedirs(os.path.dirname(a.keluar) or ".", exist_ok=True)
    R.to_csv(a.keluar, index=False, float_format="%.4g")
    print("\n" + R.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    for kol in a.fitur:
        Rk = R[(R["fitur"] == kol) & (R["laju_target"] != "asli")]
        lulus = Rk[Rk["akurasi"] >= TARGET_AKURASI]
        if len(lulus):
            print(f"\n{kol}: laju terendah dengan akurasi >= 90% = {lulus['laju_nyata'].min():.1f} paket/s "
                  f"(beacon AP ~{LAJU_BEACON} paket/s -> "
                  f"{'cukup' if lulus['laju_nyata'].min() <= LAJU_BEACON else 'TIDAK cukup'})")
        else:
            print(f"\n{kol}: tidak ada laju uji yang mencapai akurasi 90%")
    print(f"\nTabel -> {a.keluar}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for kol in a.fitur:
        Rk = R[R["fitur"] == kol].sort_values("laju_nyata")
        ax.plot(Rk["laju_nyata"], Rk["akurasi"], "o-", label=kol)
    ax.axhline(TARGET_AKURASI, color="k", ls="--", lw=1, label="target 90%")
    ax.axvline(LAJU_BEACON, color="tab:gray", ls=":", lw=1.2, label=f"beacon AP {LAJU_BEACON}")
    ax.axvline(LAJU_CASE_A, color="tab:gray", ls="-.", lw=1, label="kebutuhan Case A 20")
    ax.set_xscale("log")
    ax.set_xlabel("laju paket (paket/s)")
    ax.set_ylabel("akurasi LOSO (kosong vs bergerak)")
    ax.set_ylim(0.4, 1.02)
    ax.legend(fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.gambar) or ".", exist_ok=True)
    fig.savefig(a.gambar, dpi=130)
    print(f"Grafik -> {a.gambar}")


if __name__ == "__main__":
    main()
