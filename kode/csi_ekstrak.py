"""Ekstraksi CSI dari rekaman HackRF (.cs8) ke CSV format bersama (case base 3.4).

Pipeline: baca per potongan -> deteksi burst (energi 1 us, ambang di atas noise floor)
-> cari L-LTF -> koreksi CFO -> FFT -> H[k] 52 subcarrier.

Contoh:
    python kode/csi_ekstrak.py data/raw/A_s1_P1_jalanlos.cs8
    python kode/csi_ekstrak.py data/raw/*.cs8 --keluar data/csi --fasa

Label diambil dari nama berkas {case}_{sesi}_{subjek}_{skenario}.cs8 (bagian terakhir),
kecuali diberikan --label.
"""
import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csi_core import FS, AMP_COLS, FASA_COLS, cari_ltf, csi_dari_ltf  # noqa: E402

BLOK = 20          # 1 us pada 20 Msps
PRA = 20           # sampel sebelum awal burst yang ikut diambil
PASCA = 400        # sampel setelah awal burst (L-STF 160 + L-LTF 160 + cadangan)


def deteksi_burst(iq, ambang_db=10.0, min_us=20):
    """Kembalikan list (awal_sampel, durasi_us) burst pada potongan iq."""
    n = len(iq) // BLOK
    p = (np.abs(iq[:n * BLOK]) ** 2).reshape(n, BLOK).mean(axis=1)
    floor = np.percentile(p, 10) + 1e-12
    aktif = p > floor * 10 ** (ambang_db / 10)
    d = np.diff(aktif.astype(np.int8), prepend=0, append=0)
    naik = np.flatnonzero(d == 1)
    turun = np.flatnonzero(d == -1)
    return [(a * BLOK, b - a) for a, b in zip(naik, turun) if b - a >= min_us]


def info_parse_nama(path):
    """Pecah nama berkas {case}_{sesi}_{subjek}_{skenario}.cs8 menjadi dict."""
    nama = os.path.splitext(os.path.basename(path))[0]
    bag = nama.split("_")
    if len(bag) >= 4:
        return {"case": bag[0], "sesi": bag[1], "subjek": bag[2], "label": "_".join(bag[3:])}
    return {"case": "", "sesi": "", "subjek": "", "label": nama}


def ekstrak(path, rho_min=0.6, ambang_db=10.0, min_us=20, potongan_s=0.5,
            fasa=False, maks_s=None):
    ukuran = os.path.getsize(path) // 2  # jumlah sampel kompleks
    total = ukuran if maks_s is None else min(ukuran, int(maks_s * FS))
    chunk = int(potongan_s * FS)
    overlap = PRA + PASCA + 200
    step = chunk - overlap
    baris = []
    n_burst = 0
    n_klip = 0
    pos = 0
    while pos < total:
        cnt = min(chunk, total - pos)
        raw = np.fromfile(path, np.int8, count=cnt * 2, offset=pos * 2)
        n_klip += int(np.count_nonzero(np.abs(raw.astype(np.int16)) >= 127))
        iq = (raw[0::2] + 1j * raw[1::2]).astype(np.complex64) / 128
        # burst dengan awal di [PRA, step+PRA) diproses di potongan ini; sisanya di potongan berikut
        akhir_valid = step + PRA if pos + cnt < total else cnt
        for awal, dur in deteksi_burst(iq, ambang_db, min_us):
            if awal >= akhir_valid or awal < PRA or awal + PASCA > len(iq):
                continue
            n_burst += 1
            seg = iq[awal - PRA: awal + PASCA]
            i, rho = cari_ltf(seg)
            if rho < rho_min or i + 128 > len(seg):
                continue
            H, cfo_hz = csi_dari_ltf(seg, i)
            p_ltf = np.mean(np.abs(seg[i:i + 128]) ** 2)
            r = [(pos + awal) / FS, 10 * np.log10(p_ltf + 1e-12), cfo_hz, rho, dur]
            r.extend(np.abs(H))
            if fasa:
                r.extend(np.angle(H))
            baris.append(r)
        pos += step if pos + cnt < total else cnt
    kolom = ["t_s", "rssi_dbfs", "cfo_hz", "rho", "durasi_us"] + AMP_COLS + (FASA_COLS if fasa else [])
    df = pd.DataFrame(baris, columns=kolom)
    stat = {"berkas": os.path.basename(path), "durasi_s": total / FS, "burst": n_burst,
            "paket_csi": len(df), "klip_frac": n_klip / max(1, 2 * total)}
    return df, stat


def ringkas_laju(df, durasi_s):
    if len(df) < 2:
        return {"laju_paket_per_s": len(df) / max(durasi_s, 1e-9), "celah_maks_s": float("nan")}
    t = df["t_s"].to_numpy()
    return {"laju_paket_per_s": len(df) / durasi_s, "celah_maks_s": float(np.max(np.diff(t)))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas", nargs="+", help="berkas .cs8 (boleh glob)")
    ap.add_argument("--keluar", default="data/csi", help="folder keluaran CSV")
    ap.add_argument("--rho-min", type=float, default=0.6)
    ap.add_argument("--ambang-db", type=float, default=10.0, help="ambang burst di atas noise floor")
    ap.add_argument("--min-us", type=int, default=20, help="durasi burst minimum (us)")
    ap.add_argument("--fasa", action="store_true", help="simpan juga fase mentah (52 kolom)")
    ap.add_argument("--label", default=None, help="paksa label (default: dari nama berkas)")
    ap.add_argument("--maks-s", type=float, default=None, help="hanya proses N detik pertama")
    a = ap.parse_args()

    paths = sorted({p for pola in a.berkas for p in glob.glob(pola)})
    if not paths:
        sys.exit("Tidak ada berkas .cs8 yang cocok.")
    os.makedirs(a.keluar, exist_ok=True)
    for p in paths:
        df, stat = ekstrak(p, a.rho_min, a.ambang_db, a.min_us, fasa=a.fasa, maks_s=a.maks_s)
        info = info_parse_nama(p)
        df["label"] = a.label or info["label"]
        df["sesi"] = info["sesi"]
        df["subjek"] = info["subjek"]
        out = os.path.join(a.keluar, os.path.splitext(os.path.basename(p))[0] + ".csv")
        df.to_csv(out, index=False, float_format="%.6g")
        stat.update(ringkas_laju(df, stat["durasi_s"]))
        print(f"{stat['berkas']}: {stat['burst']} burst, {stat['paket_csi']} paket CSI "
              f"(rho>{a.rho_min}), {stat['laju_paket_per_s']:.1f} paket/s, "
              f"celah maks {stat['celah_maks_s']:.3f} s, klip {stat['klip_frac']*100:.3f}% -> {out}")


if __name__ == "__main__":
    main()
