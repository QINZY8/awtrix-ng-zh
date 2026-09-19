"""Compare a Chinese station against an international one over the same window.

Both are 64-128 kbit/s MP3. If the international stream holds its rate and the
Chinese one does not, the problem is the source rather than the device or the
local network.
"""
import socket
import sys
import time

NEEDED_BPS = 8000
SECONDS = 60.0
TIMEOUT = 15

TARGETS = [
    ("北京交通 (CN)", "lhttp.qingting.fm", 80, "/live/1291/64k.mp3"),
    ("丹阳电台 (CN)", "lhttp.qingting.fm", 80, "/live/4905/64k.mp3"),
    ("RadioParadise (US)", "stream.radioparadise.com", 80, "/mp3-128"),
    ("SomaFM (US)", "ice1.somafm.com", 80, "/groovesalad-128-mp3"),
]


def measure(label, host, port, path):
    try:
        sock = socket.create_connection((host, port), TIMEOUT)
    except OSError as exc:
        return label, None, f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return label, None, "no head"
            buf += chunk
        head, _, body = buf.partition(b"\r\n\r\n")
        if "200" not in head.decode("latin-1", "replace").splitlines()[0]:
            return label, None, "not 200"

        total = len(body)
        start = time.time()
        window_start = start
        window_bytes = len(body)
        per_second = []
        stalls = 0

        while time.time() - start < SECONDS:
            try:
                chunk = sock.recv(16384)
            except socket.timeout:
                stalls += 1
                now = time.time()
                if now - window_start >= 1.0:
                    per_second.append(window_bytes / (now - window_start))
                    window_start = now
                    window_bytes = 0
                continue
            if not chunk:
                break
            total += len(chunk)
            window_bytes += len(chunk)
            now = time.time()
            if now - window_start >= 1.0:
                per_second.append(window_bytes / (now - window_start))
                window_start = now
                window_bytes = 0
        span = time.time() - start
        if not per_second:
            return label, None, "no samples"
        below = sum(1 for b in per_second if b < NEEDED_BPS)
        return label, {
            "avg": total / span,
            "below_pct": below / len(per_second) * 100,
            "min": min(per_second),
            "samples": len(per_second),
            "stalls": stalls,
        }, ""
    finally:
        sock.close()


print(f"{'target':<22} {'avg B/s':>8} {'below%':>7} {'min B/s':>8} {'stalls':>7}")
print("-" * 58)
for label, host, port, path in TARGETS:
    name, m, err = measure(label, host, port, path)
    if not m:
        print(f"{name:<22} {'-':>8} {'-':>7} {'-':>8} {'-':>7}  {err[:20]}")
        continue
    print(f"{name:<22} {m['avg']:>8.0f} {m['below_pct']:>6.0f}% {m['min']:>8.0f} "
          f"{m['stalls']:>7}")
    time.sleep(2)
