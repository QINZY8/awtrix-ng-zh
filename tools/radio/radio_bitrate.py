"""Compare the delivery rate of the available bitrates for one station.

The 64k endpoint under-delivers on this network, which starves the decoder: the
device plays at a fixed 44.1 kHz no matter what arrives, so a stream that
delivers less than it claims drains the input buffer until it underruns. A
higher bitrate endpoint has more headroom to absorb the shortfall.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1291"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
TIMEOUT = 10

RATES = ["24k", "32k", "48k", "64k", "128k"]


def measure(rate):
    path = f"/live/{CHANNEL}/{rate}.mp3"
    try:
        sock = socket.create_connection((HOST, 80), TIMEOUT)
    except OSError as exc:
        return rate, None, f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return rate, None, "no head"
            buf += chunk
        head, _, body = buf.partition(b"\r\n\r\n")
        status = head.decode("latin-1", "replace").splitlines()[0]
        if "200" not in status:
            return rate, None, status
        total = len(body)
        start = time.time()
        while time.time() - start < SECONDS:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            total += len(chunk)
        span = time.time() - start
        return rate, total / span / 1024, ""
    finally:
        sock.close()


def main():
    print(f"channel {CHANNEL}, {SECONDS:.0f}s per rate\n")
    print(f"{'rate':<6} {'KB/s':>7} {'kbit/s':>7}  verdict")
    print("-" * 46)
    for rate in RATES:
        r, kbs, err = measure(rate)
        if kbs is None:
            print(f"{r:<6} {'-':>7} {'-':>7}  {err[:30]}")
            continue
        kbit = kbs * 8
        # The decoder consumes at the stream's own sample rate, so what matters is
        # whether delivery keeps up with the nominal bitrate.
        nominal = int(rate[:-1])
        verdict = "OK" if kbit >= nominal * 0.95 else f"UNDER by {nominal - kbit:.0f} kbit/s"
        print(f"{r:<6} {kbs:>7.1f} {kbit:>7.0f}  {verdict}")


if __name__ == "__main__":
    main()
