"""Cek cepat rekaman uji (daftar periksa 10.2 dan target minggu 1).

Memeriksa clipping ADC, jumlah paket dengan rho > 0.6 (target minggu 1: minimal 20),
laju paket aktual dibandingkan kebutuhan Case A (20 paket/s), dan sebaran CFO/daya
untuk membantu memisahkan pemancar.

Contoh:
    hackrf_transfer -r data/raw/uji_ch6.cs8 -f 2437000000 -s 20000000 -b 20000000 -l 40 -g 26 -a 0 -n 200000000
    python kode/cek_rekaman.py data/raw/uji_ch6.cs8
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csi_ekstrak import ekstrak  # noqa: E402

KEBUTUHAN_CASE_A = 20.0  # paket/s (tabel 2.4 dan ringkasan case)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("berkas")
    ap.add_argument("--maks-s", type=float, default=10.0, help="detik yang diperiksa")
    ap.add_argument("--rho-min", type=float, default=0.6)
    a = ap.parse_args()

    df, st = ekstrak(a.berkas, rho_min=a.rho_min, maks_s=a.maks_s)
    laju = len(df) / st["durasi_s"]
    print(f"Berkas          : {st['berkas']} ({st['durasi_s']:.1f} s diperiksa)")
    print(f"Clipping        : {st['klip_frac']*100:.3f}% sampel di +/-127 "
          f"{'(OK)' if st['klip_frac'] < 1e-4 else '(TURUNKAN GAIN -l/-g)'}")
    print(f"Burst terdeteksi: {st['burst']}")
    print(f"Paket CSI       : {len(df)} dengan rho > {a.rho_min} "
          f"{'(OK, >= 20)' if len(df) >= 20 else '(BELUM, target minggu 1 >= 20)'}")
    print(f"Laju paket      : {laju:.1f} paket/s vs kebutuhan Case A {KEBUTUHAN_CASE_A:.0f} paket/s "
          f"{'(OK)' if laju >= KEBUTUHAN_CASE_A else '(KURANG: naikkan laju ping / cek pemancar)'}")
    if st["burst"] > 0 and len(df) == 0:
        print("Ada burst tetapi tidak ada L-LTF valid. Di 2.4 GHz kemungkinan frame 802.11b: pindah ke 5 GHz.")
    if len(df):
        print("\nSebaran untuk memisahkan pemancar (persentil 10/50/90):")
        for kol in ["rssi_dbfs", "cfo_hz", "durasi_us", "rho"]:
            q = np.percentile(df[kol], [10, 50, 90])
            print(f"  {kol:10s}: {q[0]:9.1f} {q[1]:9.1f} {q[2]:9.1f}")


if __name__ == "__main__":
    main()
