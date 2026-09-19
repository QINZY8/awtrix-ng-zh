"""Measure one station at a time, with no other traffic competing.

The parallel ranking run had six sockets open at once, so each station's numbers
were depressed by the others. This measures a single station alone, which is the
condition the device actually plays in.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
NEEDED_BPS = 8000
SECONDS = 40.0
TIMEOUT = 15


def measure(channel, seconds=SECONDS):
    path = f"/live/{channel}/64k.mp3"
    sock = socket.create_connection((HOST, 80), TIMEOUT)
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            buf += chunk
        _, _, body = buf.partition(b"\r\n\r\n")

        total = len(body)
        start = time.time()
        window_start = start
        window_bytes = len(body)
        per_second = []

        while time.time() - start < seconds:
            try:
                chunk = sock.recv(16384)
            except socket.timeout:
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
            return None
        below = sum(1 for b in per_second if b < NEEDED_BPS)
        return {
            "avg": total / span,
            "below_pct": below / len(per_second) * 100,
            "min": min(per_second),
            "samples": len(per_second),
            "span": span,
        }
    finally:
        sock.close()


for channel in sys.argv[1:]:
    m = measure(channel)
    if not m:
        print(f"{channel}: no data")
        continue
    print(f"channel {channel:>5}  avg {m['avg']:>7.0f} B/s  "
          f"below {m['below_pct']:>3.0f}%  min {m['min']:>7.0f} B/s  "
          f"({m['samples']} samples over {m['span']:.0f}s)")
    time.sleep(2)
