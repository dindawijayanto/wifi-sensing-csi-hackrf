"""Pembangkit trafik ke hotspot untuk Windows (ping -t hanya 1 paket/s).

Mengirim paket UDP kecil ke IP hotspot sekitar 100 paket/s tanpa hak admin.
Hentikan dengan Ctrl+C.

Contoh:
    python kode/trafik.py 192.168.43.1
    python kode/trafik.py 192.168.43.1 --laju 200
"""
import argparse
import socket
import time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ip", help="IP hotspot (Default Gateway di ipconfig)")
    ap.add_argument("--laju", type=float, default=100.0, help="paket per detik")
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    jeda = 1.0 / a.laju
    n, t0 = 0, time.perf_counter()
    try:
        while True:
            s.sendto(b"x" * 100, (a.ip, 9))
            n += 1
            if n % 500 == 0:
                print(f"{n} paket terkirim, {n / (time.perf_counter() - t0):.0f} paket/s")
            time.sleep(max(0.0, t0 + n * jeda - time.perf_counter()))
    except KeyboardInterrupt:
        print(f"\nBerhenti: {n} paket terkirim.")


if __name__ == "__main__":
    main()
