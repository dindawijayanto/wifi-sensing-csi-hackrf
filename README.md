# Wi-Fi Sensing Berbasis CSI dengan HackRF: Case A (Deteksi Kehadiran dan Gerakan)

Proyek akhir mata kuliah Jaringan Nirkabel. Kami membangun penerima CSI sendiri dari sampel I/Q
mentah HackRF One (receive-only), lalu memakainya untuk menjawab:

> Apakah CSI dapat membedakan **ruang kosong**, **ada orang diam**, dan **ada orang bergerak**
> dengan lebih baik daripada RSSI?

Deadline seluruh luaran: **Selasa, 1 Desember 2026, 00:00 WIB**.

## Struktur repo

```
README.md
docs/
  proposal.md            draf proposal minggu 1 (8 poin wajib)
  pembagian_tugas.md     pembagian tim dan jadwal padat 23-30 Nov
kode/
  csi_core.py            estimasi CSI dari L-LTF (kode case base 3.3) + phase sanitization
  csi_ekstrak.py         .cs8 -> CSV format bersama (deteksi burst, L-LTF, CFO, H[k])
  cek_rekaman.py         cek cepat rekaman uji: clipping, paket rho>0.6, laju paket
  fitur.py               pilih pemancar, Hampel, resampling, fitur variansi CSI vs RSSI per jendela
  klasifikasi.py         detektor ambang kosong vs bergerak, leave-one-session-out
  visual.py              heatmap waktu x subcarrier dan sebaran fitur
tests/
  test_sintetis.py       uji seluruh pipeline dengan sinyal 802.11 sintetis (tanpa HackRF)
data/
  log_sesi.csv           log setiap sesi rekaman (wajib diisi)
  jadwal_protokol.csv    jadwal skenario per sesi
  csi/                   CSV hasil ekstraksi (di-commit)
  contoh_cs8/            1 contoh .cs8 per skenario (TIDAK di-commit, simpan di drive bersama)
  raw/                   rekaman mentah sementara (TIDAK di-commit)
hasil/
  grafik/                *.png
  tabel/                 *.csv
```

## Instalasi

```bash
python -m pip install -r requirements.txt
```

HackRF: pasang `hackrf` tools (`hackrf_info` harus mendeteksi perangkat).

## Alur kerja

### 0. Uji pipeline tanpa HackRF

```bash
python tests/test_sintetis.py
```

Harus berakhir dengan `SEMUA UJI LULUS` (galat bentuk |H| sekitar 3%, akurasi detektor sintetis 1.0).

### 1. Rekam uji 10 detik dan cek

```bash
# hotspot di kanal 6 (2437 MHz). Untuk 5 GHz: f = 5000 + 5 x kanal (MHz), mis. kanal 36 = 5180 MHz
hackrf_transfer -r data/raw/uji_ch6.cs8 -f 2437000000 -s 20000000 -b 20000000 -l 40 -g 26 -a 0 -n 200000000
python kode/cek_rekaman.py data/raw/uji_ch6.cs8
```

Target minggu 1: minimal 20 paket dengan `rho > 0.6`, tanpa clipping, dan laju paket di atas 20 paket/s.
Jika di 2.4 GHz ada burst tetapi tidak ada paket CSI, frame-nya kemungkinan 802.11b: pindah ke 5 GHz.

Trafik dari laptop: `ping -i 0.01 <ip_hotspot>` (Linux/macOS) atau `ping -t <ip_hotspot>` (Windows, lebih lambat).

### 2. Rekam sesi (60 s per skenario, gain dikunci)

Nama berkas: `{case}_{sesi}_{subjek}_{skenario}.cs8`, skenario: `kosong`, `duduk_los`, `jalan_los`, `jalan_luar`.

```bash
hackrf_transfer -r data/raw/A_s1_P1_jalan_los.cs8 -f 2437000000 -s 20000000 -b 20000000 -l 40 -g 26 -a 0 -n 1200000000
```

Isi `data/log_sesi.csv` setiap sesi. Satu rekaman 60 s = 2.4 GB, jadi langsung ekstrak lalu hapus mentahnya.

### 3. Ekstraksi CSI

```bash
python kode/csi_ekstrak.py "data/raw/*.cs8" --keluar data/csi
```

Keluaran mengikuti format bersama (case base 3.4): `t_s, rssi_dbfs, cfo_hz, rho, amp_k-26..amp_k26`
(+ `fasa_k*` dengan `--fasa`), ditambah `durasi_us`, `label`, `sesi`, `subjek`.

### 4. Fitur, deteksi, grafik

```bash
# lihat sebaran rssi/cfo di cek_rekaman.py untuk menentukan filter pemancar target
python kode/fitur.py "data/csi/*.csv" --rssi-min -45 --jendela 1.0
python kode/klasifikasi.py data/fitur.csv
python kode/visual.py heatmap "data/csi/*.csv"
python kode/visual.py fitur data/fitur.csv
```

`klasifikasi.py` memilih ambang hanya dari sesi latih lalu menguji pada sesi yang ditahan
(leave-one-session-out), untuk fitur CSI dan RSSI, dan melaporkan akurasi, FPR, dan FNR.

## Aturan data dan etika

- HackRF hanya menerima. Mode TX (`-t`) dilarang.
- Payload trafik tidak didekode; yang diolah hanya preamble, daya, dan waktu.
- Subjek memakai kode anonim (P1, P2, ...) dan menandatangani persetujuan.
- Berkas `.cs8` tidak di-commit (lihat `.gitignore`); simpan contoh di drive bersama.
