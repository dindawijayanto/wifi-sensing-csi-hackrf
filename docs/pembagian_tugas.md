# Pembagian Tugas dan Jadwal Padat

Satu kelompok, 16 anggota, Case A. Minggu 1 sudah lewat, jadi minggu 1 dan 2 dipadatkan ke
**Senin 23 Nov sampai Sabtu 28 Nov**, Minggu-Senin 29-30 Nov untuk laporan, slide, dan gladi.
Deadline semua luaran: **Selasa 1 Des 2026 00:00 WIB** (artinya Senin 30 Nov malam).

Tracker resmi ada di Google Sheet [JARNIR] tab *Task Tracker*. Dokumen ini hanya ringkasan.

## Tim

Pembagian bisa ditukar asal tracker ikut diperbarui. Semua anggota juga bergantian menjadi subjek atau
pengawas saat sesi rekaman.

| Tim | Anggota | Tanggung jawab |
|---|---|---|
| T1 Rekam dan Hardware | Bagas, Yoga, Marvin, Farhan | HackRF, hotspot, laju paket, pemisahan pemancar, sesi rekaman, log sesi, ekstraksi di lokasi |
| T2 Pipeline CSI | Faruqi, Zaid, Dinda, Priyambodo | repo, csi_ekstrak, validasi CSI, resampling, README, demo |
| T3 Analisis dan Eksplorasi | Micheline, Nafis, Benedictus (Giri), Taqiya | desain eksperimen, heatmap, fitur, detektor, eksplorasi |
| T4 Dokumen dan Presentasi | Putri, Mayu, Rajwa, Faris | proposal, kritik silang, persetujuan subjek, laporan, slide, submit |

## Jadwal

| Tanggal | Fokus | Gerbang (harus terpenuhi) |
|---|---|---|
| Sen 23 Nov | Kickoff, repo, environment, siapkan HackRF + hotspot | Semua bisa menjalankan `tests/test_sintetis.py` |
| Sel 24 Nov | Rekam uji, ekstraksi CSI, ukur laju paket, sketsa gagasan, desain eksperimen | >= 20 paket rho > 0.6, laju >= 20 paket/s, kanal dipilih (2.4 atau 5 GHz) |
| Rab 25 Nov | Proposal final + tanggapan kritik, izin ruangan, persetujuan subjek | Proposal dikumpulkan di Brone |
| Kam 26 Nov | Sesi rekaman 1 (4 skenario x 60 s), ekstraksi langsung | CSV sesi 1 ada di `data/csi` |
| Jum 27 Nov | Sesi 2 dan 3, rekaman eksplorasi, checkpoint dosen, heatmap | Data mentah + plot pertama ditunjukkan ke dosen |
| Sab 28 Nov | Fitur, detektor LOSO, pembanding RSSI, eksplorasi | Tabel akurasi/FPR/FNR CSI vs RSSI |
| Min 29 Nov | Laporan, slide, README, skrip demo | Draf laporan dan slide lengkap |
| Sen 30 Nov | Gladi presentasi + demo, review akhir, submit | Semua luaran terkumpul sebelum 23:59 |
