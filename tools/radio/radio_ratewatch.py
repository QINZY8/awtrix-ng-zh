"""Watch a stream's delivery rate over a longer window to find dips.

A short measurement can land inside a good patch and miss the problem. This
samples the delivered bytes once a second so the bad seconds are visible, which
is what the device actually experiences.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1291"
RATE = sys.argv[2] if len(sys.argv) > 2 else "64k"
SECONDS = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
TIMEOUT = 10


def main():
    path = f"/live/{CHANNEL}/{RATE}.mp3"
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

    print(f"channel {CHANNEL} at {RATE}, per-second delivery (KB/s)\n")
    start = time.time()
    window_start = start
    window_bytes = len(body)
    total = len(body)
    per_second = []

    while time.time() - start < SECONDS:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            print("  timeout")
            break
        if not chunk:
            print("  closed")
            break
        window_bytes += len(chunk)
        total += len(chunk)
        now = time.time()
        if now - window_start >= 1.0:
            kbs = window_bytes / (now - window_start) / 1024
            per_second.append(kbs)
            bar = "#" * int(kbs * 2)
            flag = "  <-- LOW" if kbs < 7.0 else ""
            print(f"  t={now - start:5.1f}s  {kbs:5.1f} KB/s  {bar}{flag}")
            window_start = now
            window_bytes = 0

    sock.close()
    span = time.time() - start
    print(f"\ntotal {total} bytes in {span:.1f} s = {total / span / 1024:.1f} KB/s "
          f"({total * 8 / span / 1000:.0f} kbit/s)")
    if per_second:
        low = [v for v in per_second if v < 7.0]
        print(f"seconds below 7 KB/s: {len(low)} / {len(per_second)}")
        print(f"min {min(per_second):.1f}  median "
              f"{sorted(per_second)[len(per_second) // 2]:.1f}  max {max(per_second):.1f} KB/s")


if __name__ == "__main__":
    main()
