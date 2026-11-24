"""Tentukan filter pemancar target (hotspot HP) dan pisahkan paket laptop ping.

Butuh dua CSV hasil csi_ekstrak.py yang direkam di posisi, kanal, dan gain yang sama:
  - beacon : hotspot menyala, laptop tersambung, ping MATI (hampir semua paket dari HP)
  - ping   : ping/trafik MENYALA (paket HP + paket laptop)

Sidik jari HP (CFO, RSSI) diambil dari rekaman beacon, lalu dipakai untuk memilah
rekaman ping. Script mencetak batas filter, laju paket HP setelah filter, dan perintah
fitur.py yang siap dipakai. Plot sebaran disimpan sebagai PNG.

Contoh:
    python kode/pisah_pemancar.py data/uji/uji_beacon.csv data/uji/uji_ping.csv
    python kode/pisah_pemancar.py data/uji/uji_beacon.csv data/uji/uji_ping.csv --lebar-cfo 4000
"""
import argparse
import os

import numpy as np
import pandas as pd

KEBUTUHAN_CASE_A = 20.0  # paket/s


def mad(x):
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def laju(df):
    if len(df) < 2:
        return 0.0
    return len(df) / max(df["t_s"].iloc[-1] - df["t_s"].iloc[0], 1e-9)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beacon", help="CSV rekaman beacon saja (ping mati)")
    ap.add_argument("ping", help="CSV rekaman dengan ping menyala")
    ap.add_argument("--lebar-cfo", type=float, default=3000.0,
                    help="setengah lebar jendela CFO minimum di sekitar median HP (Hz)")
    ap.add_argument("--plot", default="hasil/gambar/pisah_pemancar.png")
    a = ap.parse_args()

    b = pd.read_csv(a.beacon)
    p = pd.read_csv(a.ping)
    if len(b) < 5:
        raise SystemExit(f"Rekaman beacon hanya {len(b)} paket CSI. Cek kanal (-f) dan hotspot, rekam ulang.")

    # 1. Sidik jari HP dari rekaman beacon
    cfo_hp = float(np.median(b["cfo_hz"]))
    rssi_hp = float(np.median(b["rssi_dbfs"]))
    lebar = max(a.lebar_cfo, 4 * mad(b["cfo_hz"].to_numpy()))
    cfo_min, cfo_max = cfo_hp - lebar, cfo_hp + lebar
    print(f"Sidik jari HP (beacon, {len(b)} paket): CFO median {cfo_hp:.0f} Hz, RSSI median {rssi_hp:.1f} dBFS")
    print(f"Jendela CFO HP: {cfo_min:.0f} .. {cfo_max:.0f} Hz")

    # 2. Pilah rekaman ping
    m_hp = p["cfo_hz"].between(cfo_min, cfo_max).to_numpy()
    hp, lain = p[m_hp], p[~m_hp]
    print(f"\nRekaman ping: {len(p)} paket CSI -> HP {len(hp)}, lainnya (laptop/AP lain) {len(lain)}")

    rssi_max = None
    if len(lain) >= 5:
        cfo_lain = float(np.median(lain["cfo_hz"]))
        rssi_lain = float(np.median(lain["rssi_dbfs"]))
        print(f"Kelompok lain: CFO median {cfo_lain:.0f} Hz, RSSI median {rssi_lain:.1f} dBFS")
        rssi_hp_ping = float(np.median(hp["rssi_dbfs"])) if len(hp) else rssi_hp
        selisih = rssi_lain - rssi_hp_ping
        if selisih > 6:  # laptop jelas lebih kuat (di samping HackRF): pakai batas atas RSSI sebagai pengaman
            rssi_max = round((rssi_hp_ping + rssi_lain) / 2, 1)
            print(f"Laptop {selisih:.1f} dB lebih kuat dari HP -> batas pengaman --rssi-max {rssi_max}")
        else:
            print(f"Selisih RSSI hanya {selisih:.1f} dB, RSSI tidak dipakai sebagai filter (andalkan CFO).")
        if abs(cfo_lain - cfo_hp) < 2 * lebar:
            print("PERINGATAN: CFO laptop dekat dengan HP. Perkecil --lebar-cfo atau cek plot sebelum dipakai.")
    else:
        print("Hampir tidak ada paket non-HP. Cek apakah ping benar-benar jalan saat rekaman ping.")

    if rssi_max is not None:
        hp = hp[hp["rssi_dbfs"] <= rssi_max]

    # 3. Durasi burst (informasi, tidak difilter secara default)
    if len(hp):
        q = np.percentile(hp["durasi_us"], [10, 50, 90])
        print(f"\nDurasi burst HP (persentil 10/50/90): {q[0]:.0f} / {q[1]:.0f} / {q[2]:.0f} us")

    # 4. Laju setelah filter
    r = laju(hp)
    status = "OK" if r >= KEBUTUHAN_CASE_A else "KURANG: naikkan laju ping atau pakai ping ICMP, bukan UDP"
    print(f"Laju paket HP setelah filter: {r:.1f} paket/s vs kebutuhan {KEBUTUHAN_CASE_A:.0f} ({status})")

    arg = f"--cfo-min {cfo_min:.0f} --cfo-max {cfo_max:.0f}"
    if rssi_max is not None:
        arg += f" --rssi-max {rssi_max}"
    print(f"\nFilter final : {arg}")
    print(f'Pemakaian    : python kode/fitur.py "data/csi/*.csv" {arg} --jendela 1.0')

    # 5. Plot sebaran
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for axi, df, judul in [(ax[0], b, "Beacon saja (ping mati)"), (ax[1], p, "Ping menyala")]:
        masuk = df["cfo_hz"].between(cfo_min, cfo_max)
        if rssi_max is not None:
            masuk &= df["rssi_dbfs"] <= rssi_max
        axi.scatter(df.loc[masuk, "cfo_hz"] / 1e3, df.loc[masuk, "rssi_dbfs"], s=6, label="HP (dipakai)")
        axi.scatter(df.loc[~masuk, "cfo_hz"] / 1e3, df.loc[~masuk, "rssi_dbfs"], s=6, label="lainnya (dibuang)")
        axi.axvspan(cfo_min / 1e3, cfo_max / 1e3, alpha=0.12)
        if rssi_max is not None:
            axi.axhline(rssi_max, ls="--", lw=1)
        axi.set_title(judul)
        axi.set_xlabel("CFO (kHz)")
        axi.legend(loc="best", fontsize=8)
    ax[0].set_ylabel("RSSI (dBFS)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(a.plot) or ".", exist_ok=True)
    fig.savefig(a.plot, dpi=130)
    print(f"Plot sebaran : {a.plot}")


if __name__ == "__main__":
    main()
