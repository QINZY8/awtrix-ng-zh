"""Measure how fast a stream actually delivers bytes, and how evenly.

A stream that arrives in bursts is what makes the device's input buffer
sawtooth: it fills in a spike, drains linearly, and underruns when the next
spike is late. This reads the socket for a fixed window and reports the
inter-arrival gaps, which is what the device actually sees.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1291"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
TIMEOUT = 10


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
            print("no response head")
            return
        buf += chunk
    head, _, body = buf.partition(b"\r\n\r\n")
    print(head.decode("latin-1", "replace").splitlines()[0])

    total = len(body)
    reads = []          # (time, bytes)
    start = time.time()
    last_time = start
    while time.time() - start < SECONDS:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            print("  socket timeout")
            break
        if not chunk:
            print("  stream closed")
            break
        now = time.time()
        reads.append((now - start, len(chunk), now - last_time))
        last_time = now
        total += len(chunk)
    sock.close()

    span = time.time() - start
    print(f"\nreceived {total} bytes in {span:.1f} s = {total / span / 1024:.1f} KB/s "
          f"({total * 8 / span / 1000:.0f} kbit/s)")

    if not reads:
        return
    gaps = [r[2] for r in reads]
    sizes = [r[1] for r in reads]
    gaps_sorted = sorted(gaps)
    print(f"\nreads: {len(reads)}")
    print(f"gap  min {min(gaps) * 1000:.1f} ms  median "
          f"{gaps_sorted[len(gaps_sorted) // 2] * 1000:.1f} ms  max {max(gaps) * 1000:.1f} ms")
    print(f"read size  min {min(sizes)}  max {max(sizes)}  avg {sum(sizes) / len(sizes):.0f}")
    print(f"gaps over 500 ms: {sum(1 for g in gaps if g > 0.5)}")
    print(f"gaps over 1000 ms: {sum(1 for g in gaps if g > 1.0)}")

    # A 64 kbit/s stream needs 8 KB/s. The device holds 64 KB, so it can ride out
    # a gap of about 8 s only if the buffer is full when the gap starts.
    print(f"\nstream needs {64 * 1000 / 8 / 1024:.1f} KB/s to play without stalling")


if __name__ == "__main__":
    main()
