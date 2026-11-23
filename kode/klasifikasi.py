"""Detektor ambang Case A (kosong vs bergerak) dengan skema leave-one-session-out.

Ambang dipilih HANYA dari sesi latih (memaksimalkan balanced accuracy), lalu diuji pada
sesi yang ditahan. Fitur CSI dan RSSI dievaluasi dengan cara yang sama agar bisa
dibandingkan.

Contoh:
    python kode/klasifikasi.py data/fitur.csv
    python kode/klasifikasi.py data/fitur.csv --bergerak jalan_los --fitur csi_var_norm rssi_var
"""
import argparse
import os

import numpy as np
import pandas as pd


def pilih_ambang(x, y):
    """Ambang yang memaksimalkan balanced accuracy pada data latih (y: 0 kosong, 1 bergerak)."""
    v = np.unique(x)
    kandidat = np.concatenate([[v[0] - 1e-12], (v[:-1] + v[1:]) / 2, [v[-1] + 1e-12]])
    terbaik, skor_terbaik = kandidat[0], -1.0
    for th in kandidat:
        pred = x > th
        tpr = pred[y == 1].mean() if (y == 1).any() else 0.0
        tnr = (~pred[y == 0]).mean() if (y == 0).any() else 0.0
        skor = (tpr + tnr) / 2
        if skor > skor_terbaik:
            terbaik, skor_terbaik = th, skor
    return float(terbaik)


def metrik(pred, y):
    tp = int(np.sum(pred & (y == 1)))
    tn = int(np.sum(~pred & (y == 0)))
    fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    n = tp + tn + fp + fn
    return {"akurasi": (tp + tn) / n if n else np.nan,
            "fpr": fp / (fp + tn) if fp + tn else np.nan,
            "fnr": fn / (fn + tp) if fn + tp else np.nan,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas_fitur", metavar="fitur.csv", help="CSV hasil fitur.py")
    ap.add_argument("--kosong", nargs="+", default=["kosong"], help="label kelas negatif")
    ap.add_argument("--bergerak", nargs="+", default=["jalan_los", "jalan_luar"], help="label kelas positif")
    ap.add_argument("--fitur", nargs="+", default=["csi_var_norm", "csi_var", "rssi_var"])
    ap.add_argument("--keluar", default="hasil/tabel/deteksi_loso.csv")
    a = ap.parse_args()

    df = pd.read_csv(a.berkas_fitur, dtype={"sesi": str})
    df = df[df["label"].isin(a.kosong + a.bergerak)].copy()
    df["y"] = df["label"].isin(a.bergerak).astype(int)
    sesi = sorted(df["sesi"].unique())
    if len(sesi) < 2:
        raise SystemExit("Butuh minimal 2 sesi untuk leave-one-session-out.")

    baris = []
    for f in a.fitur:
        for s in sesi:
            latih, uji = df[df["sesi"] != s], df[df["sesi"] == s]
            if latih["y"].nunique() < 2 or uji.empty:
                continue
            th = pilih_ambang(latih[f].to_numpy(), latih["y"].to_numpy())
            m = metrik(uji[f].to_numpy() > th, uji["y"].to_numpy())
            baris.append({"fitur": f, "sesi_uji": s, "ambang": th, "n_uji": len(uji), **m})
    hasil = pd.DataFrame(baris)
    os.makedirs(os.path.dirname(a.keluar) or ".", exist_ok=True)
    hasil.to_csv(a.keluar, index=False, float_format="%.4g")

    ringkas = hasil.groupby("fitur")[["akurasi", "fpr", "fnr"]].mean()
    print("Per fold:\n", hasil.to_string(index=False))
    print("\nRata-rata leave-one-session-out:\n", ringkas.to_string(float_format=lambda v: f"{v:.3f}"))
    print(f"\nTabel -> {a.keluar}")


if __name__ == "__main__":
    main()
