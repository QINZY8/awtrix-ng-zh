"""Check whether the station closes or stalls the connection after a while.

The 64k endpoints stop delivering after roughly ten seconds in these tests. If
the server is dropping idle-ish connections, the device's own reconnect logic
has to cover the gap, and every reconnect is an audible break - which is exactly
the stutter that is being heard.
"""
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
CHANNELS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["1291", "273", "4930"]
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
TIMEOUT = 12


def watch(channel, rate="64k"):
    path = f"/live/{channel}/{rate}.mp3"
    try:
        sock = socket.create_connection((HOST, 80), TIMEOUT)
    except OSError as exc:
        return f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return "no head"
            buf += chunk
        _, _, body = buf.partition(b"\r\n\r\n")
        total = len(body)
        start = time.time()
        last = start
        while time.time() - start < SECONDS:
            try:
                chunk = sock.recv(8192)
            except socket.timeout:
                return (f"STALLED after {last - start:.1f}s "
                        f"({total} bytes, {total / (last - start) / 1024:.1f} KB/s)")
            if not chunk:
                return (f"CLOSED after {last - start:.1f}s "
                        f"({total} bytes, {total / (last - start) / 1024:.1f} KB/s)")
            total += len(chunk)
            last = time.time()
        return (f"alive the whole {SECONDS:.0f}s "
                f"({total} bytes, {total / SECONDS / 1024:.1f} KB/s)")
    finally:
        sock.close()


for ch in CHANNELS:
    print(f"channel {ch}: {watch(ch)}")
