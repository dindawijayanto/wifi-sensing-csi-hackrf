"""Fungsi inti estimasi CSI dari L-LTF 802.11 (diambil dari case base bagian 3.3).

Semua skrip lain mengimpor modul ini supaya hanya ada satu implementasi
estimasi CSI di repo.
"""
import numpy as np

FS = 20e6  # sample rate HackRF = sample rate native 802.11 20 MHz

# L-LTF domain frekuensi, subcarrier -26..+26 (IEEE 802.11)
L = np.array([1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 0,
              1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, 1, 1, 1, 1],
             float)
K = np.arange(-26, 27)
X = np.zeros(64, complex)
X[K % 64] = L
ltf = np.fft.ifft(X)            # 1 simbol LTF, 64 sampel
IDX = K[K != 0] % 64            # 52 subcarrier terisi
SUBCARRIER = K[K != 0]          # -26..-1, 1..26

AMP_COLS = [f"amp_k{k}" for k in SUBCARRIER]
FASA_COLS = [f"fasa_k{k}" for k in SUBCARRIER]


def baca_cs8(path, mulai_s=0.0, durasi_s=1.0, fs=FS):
    """Baca potongan rekaman hackrf_transfer (.cs8, int8 I/Q berselang-seling)."""
    off = int(mulai_s * fs) * 2
    raw = np.fromfile(path, np.int8, count=int(durasi_s * fs) * 2, offset=off)
    return (raw[0::2] + 1j * raw[1::2]).astype(np.complex64) / 128


def cari_ltf(seg):
    """Indeks awal simbol LTF pertama pada potongan sinyal (dimulai sedikit sebelum burst)."""
    e = np.sqrt(np.convolve(np.abs(seg) ** 2, np.ones(64), 'valid'))
    rho = np.abs(np.correlate(seg, ltf, 'valid')) / (np.linalg.norm(ltf) * e + 1e-12)
    i = int(np.argmax(rho))
    if i >= 64 and rho[i - 64] > 0.7 * rho[i]:  # dua puncak berjarak 64, ambil yang pertama
        i -= 64
    return i, float(rho[i])


def csi_dari_ltf(seg, i):
    """CSI 52 subcarrier dan CFO (Hz) dari dua simbol LTF yang dimulai di indeks i."""
    s1, s2 = seg[i:i + 64], seg[i + 64:i + 128]
    cfo = np.angle(np.vdot(s1, s2)) / 64  # rad/sampel
    s = seg[i:i + 128] * np.exp(-1j * cfo * np.arange(128))
    Y = (np.fft.fft(s[:64]) + np.fft.fft(s[64:])) / 2
    return Y[IDX] / X[IDX], cfo * FS / (2 * np.pi)


def sanitasi_fase(H):
    """Phase sanitization (bagian 2.3): unwrap terhadap k lalu buang garis a*k + b.

    H: array (..., 52). Mengembalikan sisa fase dengan bentuk yang sama.
    Hanya sahih untuk perbandingan relatif antarpaket.
    """
    ph = np.unwrap(np.angle(H), axis=-1)
    k = SUBCARRIER.astype(float)
    A = np.vstack([k, np.ones_like(k)]).T
    coef, *_ = np.linalg.lstsq(A, ph.reshape(-1, 52).T, rcond=None)
    garis = (A @ coef).T.reshape(ph.shape)
    return ph - garis
