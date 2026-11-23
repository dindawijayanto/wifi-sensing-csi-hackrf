# Proposal Minggu 1: Case A, Deteksi Kehadiran dan Gerakan dengan CSI

> Draf. Bagian bertanda **[ISI]** diisi setelah rekaman uji 24 Nov. Maksimal 2 halaman saat diekspor ke PDF.

## 1. Case yang dipilih dan alasannya

Case A (Dasar, 20 paket/s, 2.4 atau 5 GHz). Alasan:

- Laju paket 20 paket/s dapat dipenuhi hotspot HP dengan `ping`, sehingga risiko teknis rendah di
  jadwal yang dipadatkan (minggu 1 dan 2 dalam 6 hari).
- Pertanyaan utamanya langsung membandingkan CSI dengan RSSI, sesuai rubrik "ada pembanding RSSI".
- Skenario tidak butuh banyak subjek atau pengulangan per subjek, jadi waktu bisa dipakai untuk eksplorasi.

## 2. Pertanyaan riset dan hipotesis

**Pertanyaan:** apakah CSI dapat membedakan ruang kosong, orang diam, dan orang bergerak lebih baik daripada RSSI?

- **H1.** Detektor ambang berbasis rata-rata variansi |H[k]| ternormalisasi (jendela 1 s) mencapai
  akurasi >= 90% dengan FPR <= 10% untuk *kosong vs bergerak* pada skema leave-one-session-out.
  *Terbantah jika* akurasi rata-rata < 90% atau FPR > 10%.
- **H2.** Pada data uji yang sama, detektor berbasis variansi RSSI memiliki akurasi paling sedikit
  10 poin persentase di bawah detektor CSI, terutama untuk skenario berjalan di luar LOS.
  *Terbantah jika* selisih akurasi < 10 poin.
- **H3.** Rata-rata fitur CSI skenario *duduk diam di LOS* berbeda dari *kosong* (uji Mann-Whitney, p < 0.05),
  walaupun lebih kecil dari skenario berjalan. *Terbantah jika* p >= 0.05.

## 3. Desain eksperimen

| Item | Rencana |
|---|---|
| Denah | Pemancar (hotspot HP) dan HackRF setinggi sekitar 1 m, terpisah 4 m. Titik D di tengah LOS, lintasan L1 memotong LOS, lintasan L2 sejajar dinding sekitar 1.5 m dari LOS. Semua posisi ditandai lakban. **[ISI denah + foto]** |
| Skenario | kosong, duduk_los, jalan_los, jalan_luar |
| Sesi | 3 sesi per skenario, 60 s per sesi (minimal case: 3 x 30 s) |
| Subjek | 3 subjek (P1-P3) bergantian per sesi, kode anonim |
| Kanal | **[ISI]** 2.4 GHz kanal 6 bila frame OFDM terbukti (rho > 0.6), selain itu 5 GHz kanal 36 |
| Gain | `-l 40 -g 26 -a 0`, dikunci untuk semua sesi (disesuaikan jika rekaman uji menunjukkan clipping) |
| Pemancar | Hotspot HP milik kelompok, kanal dikunci; laptop menjalankan `ping -i 0.01` |
| Laju paket | Target >= 50 paket/s (2.5x kebutuhan 20 paket/s). Terukur pada uji: **[ISI] paket/s** |
| Kontrol | Tidak ada orang lain di ruangan saat baseline, pintu tertutup, kondisi dicatat di `log_sesi.csv` |

## 4. Metrik keberhasilan

- Akurasi, FPR, dan FNR detektor kosong vs bergerak pada data uji yang tidak dipakai menentukan ambang.
- Rasio median fitur CSI bergerak/kosong dan RSSI bergerak/kosong.
- Laju paket aktual dan celah terpanjang per sesi.

## 5. Skema pembagian data latih dan uji

Leave-one-session-out: ambang dipilih dari 2 sesi, diuji di sesi ke-3, diulang 3 kali. Jendela dari sesi
yang sama tidak pernah dipecah ke latih dan uji. Bila subjek berbeda per sesi, skema ini sekaligus menguji
perpindahan subjek.

## 6. Gagasan eksplorasi

**Batas laju paket untuk beacon AP.** Data hotspot di-*downsample* bertahap (50, 20, 10, 5 paket/s) untuk
mencari laju terendah yang masih memberi akurasi >= 90%, lalu dibandingkan dengan beacon AP (sekitar 9.77 paket/s).
Cadangan jika waktu cukup: menghitung orang (0-3 orang bergerak) untuk melihat apakah fitur CSI naik secara monoton.

## 7. Tanggapan atas kritik kelompok lain

| Kritik/saran | Tanggapan dan bagian yang diubah |
|---|---|
| **[ISI]** | |
| **[ISI]** | |
| **[ISI saran]** | |

## 8. Pembagian tugas anggota

Lihat `docs/pembagian_tugas.md` dan tab Task Tracker di Google Sheet [JARNIR].

| Tim | Anggota |
|---|---|
| Rekam dan Hardware | Bagas Aditha Pratama, Yoga Kurniawan, Marvin Ligarta, M. Farhan Zaky |
| Pipeline CSI | Faruqi Akbar, Muhammad Zaid Robbani, Dinda Anggraini Wijayanto, Priyambodo Arundaya Satmika |
| Analisis dan Eksplorasi | Micheline Keiza Andrea Pangemanan, Nafis Naufal Rahman, Benedictus Giri Cahya Saputra, Taqiya Sakha Putri |
| Dokumen dan Presentasi | Putri Aulia Sari, Mayu Septania Anjani, Rajwa Nadia Lathifa, Faris Muhammad Mada Dziban |
