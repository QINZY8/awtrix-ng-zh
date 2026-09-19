"""Measure the true delivered byte rate of a station over several minutes.

The device's buffer drains to zero repeatedly, which means delivery falls below
8000 bytes/s often enough to empty 64 KB. A short probe can miss this, so this
samples the cumulative byte count once a second for a long window and reports
how often delivery dips below what playback needs.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1291"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
TIMEOUT = 15
NEEDED_BPS = 8000          # 64 kbit/s


def main():
    path = f"/live/{CHANNEL}/64k.mp3"
    sock = socket.create_connection((HOST, 80), TIMEOUT)
    sock.settimeout(TIMEOUT)
    req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
           "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
    sock.sendall(req.encode())

    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            print("no head")
            return
        buf += chunk
    _, _, body = buf.partition(b"\r\n\r\n")

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
                bps = window_bytes / (now - window_start)
                per_second.append(bps)
                window_start = now
                window_bytes = 0
            continue
        if not chunk:
            print("stream closed")
            break
        total += len(chunk)
        window_bytes += len(chunk)
        now = time.time()
        if now - window_start >= 1.0:
            bps = window_bytes / (now - window_start)
            per_second.append(bps)
            window_start = now
            window_bytes = 0
    sock.close()

    span = time.time() - start
    print(f"channel {CHANNEL}, {span:.0f} s, {total} bytes")
    print(f"average {total / span:.0f} bytes/s  (playback needs {NEEDED_BPS})\n")
    if not per_second:
        print("no full seconds sampled")
        return

    below = [b for b in per_second if b < NEEDED_BPS]
    print(f"per-second samples: {len(per_second)}")
    print(f"below {NEEDED_BPS} B/s:   {len(below)}  ({len(below) / len(per_second) * 100:.0f}%)")
    print(f"min {min(per_second):.0f}  median "
          f"{sorted(per_second)[len(per_second) // 2]:.0f}  max {max(per_second):.0f} bytes/s")
    print(f"socket stalls:      {stalls}")

    # A second below the needed rate costs (needed - actual) bytes from the buffer.
    deficit = sum(NEEDED_BPS - b for b in below)
    print(f"\ntotal deficit:      {deficit:.0f} bytes")
    print(f"buffer size:        65536 bytes")
    if deficit > 65536:
        print("verdict: the deficit exceeds the buffer, so playback must underrun")
    elif deficit > 0:
        print("verdict: the deficit is absorbed by the buffer, but only just")
    else:
        print("verdict: delivery keeps up on average")

    print("\nworst seconds:")
    for b in sorted(per_second)[:10]:
        print(f"  {b:7.0f} bytes/s")


if __name__ == "__main__":
    main()
