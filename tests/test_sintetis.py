"""Uji pipeline dengan sinyal sintetis (tanpa HackRF).

1. Membuat paket 802.11 sintetis (L-STF + L-LTF + payload acak) yang melewati kanal
   multipath, CFO, dan noise, lalu disimpan sebagai .cs8 int8 seperti hackrf_transfer.
2. Memeriksa csi_ekstrak menemukan paket dan |H[k]| cocok dengan kanal sebenarnya.
3. Menjalankan fitur.py + klasifikasi.py: skenario "bergerak" (lintasan dinamis berputar)
   harus terpisah dari "kosong" (kanal statis).

Jalankan dari root repo:  python tests/test_sintetis.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "kode"))
from csi_core import FS, IDX, ltf, AMP_COLS  # noqa: E402
from csi_ekstrak import ekstrak  # noqa: E402

rng = np.random.default_rng(7)


def stf():
    S = np.zeros(64, complex)
    S[np.arange(-24, 25, 4) % 64] = rng.choice([1 + 1j, -1 - 1j], 13)
    S[0] = 0
    s16 = np.fft.ifft(S)[:16]
    return np.tile(s16, 10)


def paket():
    payload = (rng.standard_normal(400) + 1j * rng.standard_normal(400)) * np.std(ltf)
    lt = np.concatenate([ltf[-32:], ltf, ltf])
    return np.concatenate([stf() * np.std(ltf) / np.std(stf()), lt, payload])


def kanal_statis():
    h = (rng.standard_normal(6) + 1j * rng.standard_normal(6)) * np.exp(-np.arange(6) / 2)
    h[0] += 2.0
    return h


def buat_cs8(path, h_statis, laju=200, durasi=0.5, bergerak=False, cfo_hz=8000, snr_db=25):
    n = int(durasi * FS)
    sig = np.zeros(n, complex)
    t_paket = np.arange(0.002, durasi - 0.002, 1 / laju)
    H_benar = []
    for t in t_paket:
        h = h_statis.copy()
        if bergerak:  # lintasan pantul tubuh dengan panjang lintasan berubah (Doppler ~20 Hz)
            h[2] += 1.2 * np.exp(-1j * 2 * np.pi * 20 * t)
        p = np.convolve(paket(), h)[:len(paket())]
        i0 = int(t * FS)
        sig[i0:i0 + len(p)] += p
        H_benar.append(np.abs(np.fft.fft(h, 64)[IDX]))
    sig *= np.exp(1j * 2 * np.pi * cfo_hz * np.arange(n) / FS)
    p_sig = np.mean(np.abs(sig[sig != 0]) ** 2)
    sig += np.sqrt(p_sig / 10 ** (snr_db / 10) / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    sig *= 40 / np.max(np.abs(sig))  # skala ke int8 tanpa clipping
    raw = np.empty(2 * n, np.int8)
    raw[0::2] = np.round(sig.real)
    raw[1::2] = np.round(sig.imag)
    raw.tofile(path)
    return t_paket, np.array(H_benar)


def main():
    tmp = tempfile.mkdtemp(prefix="csi_sint_")
    try:
        h = kanal_statis()
        raw_dir = os.path.join(tmp, "raw")
        os.makedirs(raw_dir)

        # --- uji akurasi ekstraksi ---
        t_ref, H_ref = buat_cs8(os.path.join(raw_dir, "A_s1_SIM_kosong.cs8"), h)
        df, st = ekstrak(os.path.join(raw_dir, "A_s1_SIM_kosong.cs8"))
        assert len(df) >= 0.95 * len(t_ref), f"paket terdeteksi {len(df)} dari {len(t_ref)}"
        A = df[AMP_COLS].to_numpy()
        bentuk_est = A / A.mean(axis=1, keepdims=True)
        bentuk_ref = H_ref[0] / H_ref[0].mean()
        galat = np.mean(np.abs(bentuk_est - bentuk_ref)) / np.mean(bentuk_ref)
        cfo_med = np.median(df["cfo_hz"])
        print(f"[ekstraksi] {len(df)}/{len(t_ref)} paket, rho median {df['rho'].median():.3f}, "
              f"galat bentuk |H| {galat*100:.2f}%, CFO median {cfo_med:.0f} Hz (benar 8000)")
        assert galat < 0.05, "galat amplitudo terlalu besar"
        assert abs(cfo_med - 8000) < 300, "estimasi CFO meleset"

        # --- uji end-to-end detektor kosong vs bergerak, 3 sesi ---
        for s in ["s2", "s3"]:
            buat_cs8(os.path.join(raw_dir, f"A_{s}_SIM_kosong.cs8"), h)
        for s in ["s1", "s2", "s3"]:
            buat_cs8(os.path.join(raw_dir, f"A_{s}_SIM_jalan_los.cs8"), h, bergerak=True)
        csi_dir = os.path.join(tmp, "csi")
        py = sys.executable
        kode = os.path.join(ROOT, "kode")
        jalan = lambda *args: subprocess.run([py, *args], check=True, cwd=tmp)  # noqa: E731
        jalan(os.path.join(kode, "csi_ekstrak.py"), os.path.join(raw_dir, "*.cs8"), "--keluar", csi_dir)
        jalan(os.path.join(kode, "fitur.py"), os.path.join(csi_dir, "*.csv"), "--jendela", "0.1",
              "--fs-grid", "200", "--keluar", "fitur.csv", "--laporan", "laju.csv")
        jalan(os.path.join(kode, "klasifikasi.py"), "fitur.csv", "--bergerak", "jalan_los",
              "--keluar", "loso.csv")
        hasil = pd.read_csv(os.path.join(tmp, "loso.csv"))
        akurasi_csi = hasil.loc[hasil["fitur"] == "csi_var_norm", "akurasi"].mean()
        print(f"[end-to-end] akurasi LOSO csi_var_norm = {akurasi_csi:.3f}")
        assert akurasi_csi > 0.9, "detektor CSI gagal memisahkan kosong vs bergerak"
        jalan(os.path.join(kode, "visual.py"), "heatmap", os.path.join(csi_dir, "A_s1_SIM_jalan_los.csv"),
              "--keluar", "grafik")
        jalan(os.path.join(kode, "visual.py"), "fitur", "fitur.csv", "--keluar", "grafik")
        print("SEMUA UJI LULUS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
