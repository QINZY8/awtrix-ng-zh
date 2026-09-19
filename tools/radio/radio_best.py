"""Find streams whose delivered rate exceeds what playback consumes, with margin.

Two things matter, and they pull in opposite directions:

  * a 64 kbit/s stream needs 8000 B/s to play, so it has a low bar to clear,
    but any dip below 8000 drains the buffer
  * a 128 kbit/s stream needs 16000 B/s, so it clears the bar more easily in
    absolute terms, but the same 64 KB buffer only covers half as many seconds
    of outage

The best stream is one whose bitrate matches the source's real capability, so
this reports the delivered rate against the rate the decoder will consume, and
the seconds of buffer cover that leaves.
"""
import socket
import sys
import time

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
TIMEOUT = 15
BUFFER_BYTES = 65536

# (label, host, port, path, nominal kbit/s)
TARGETS = [
    ("SomaFM Lush 128k", "ice1.somafm.com", 80, "/lush-128-mp3", 128),
    ("SomaFM Groove 128k", "ice1.somafm.com", 80, "/groovesalad-128-mp3", 128),
    ("SomaFM Drone 64k", "ice1.somafm.com", 80, "/dronezone-64-mp3", 64),
    ("SomaFM Indie 64k", "ice1.somafm.com", 80, "/indiepop-64-mp3", 64),
    ("SomaFM Beat 64k", "ice1.somafm.com", 80, "/beatblender-64-mp3", 64),
    ("RadioParadise 128k", "stream.radioparadise.com", 80, "/mp3-128", 128),
    ("RadioParadise 64k", "stream.radioparadise.com", 80, "/mp3-64", 64),
    ("南通交通 64k", "lhttp.qingting.fm", 80, "/live/1155/64k.mp3", 64),
    ("镇江交通 64k", "lhttp.qingting.fm", 80, "/live/1158/64k.mp3", 64),
]


def measure(label, host, port, path, nominal_kbit):
    needed = nominal_kbit * 1000 / 8
    try:
        sock = socket.create_connection((host, port), TIMEOUT)
    except OSError as exc:
        return label, nominal_kbit, None, f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return label, nominal_kbit, None, "no head"
            buf += chunk
        head, _, body = buf.partition(b"\r\n\r\n")
        if "200" not in head.decode("latin-1", "replace").splitlines()[0]:
            return label, nominal_kbit, None, "not 200"

        total = len(body)
        start = time.time()
        window_start = start
        window_bytes = len(body)
        per_second = []

        while time.time() - start < SECONDS:
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
            return label, nominal_kbit, None, "no samples"
        below = sum(1 for b in per_second if b < needed)
        return label, nominal_kbit, {
            "needed": needed,
            "avg": total / span,
            "below_pct": below / len(per_second) * 100,
            "min": min(per_second),
            "samples": len(per_second),
            "cover_s": BUFFER_BYTES / needed,
        }, ""
    finally:
        sock.close()


print(f"{'stream':<22} {'need':>6} {'avg':>7} {'below%':>7} {'min':>7} {'cover':>6}")
print("-" * 62)
results = []
for label, host, port, path, nominal in TARGETS:
    name, nominal, m, err = measure(label, host, port, path, nominal)
    if not m:
        print(f"{name:<22} {nominal:>5}k {'-':>7} {'-':>7} {'-':>7} {'-':>6}  {err[:16]}")
        continue
    results.append((name, m))
    print(f"{name:<22} {m['needed']:>5.0f} {m['avg']:>7.0f} {m['below_pct']:>6.0f}% "
          f"{m['min']:>7.0f} {m['cover_s']:>5.1f}s")
    time.sleep(1)

print("\n== ranked: fewest under-delivering seconds, then most buffer cover ==")
for name, m in sorted(results, key=lambda r: (r[1]["below_pct"], -r[1]["cover_s"])):
    print(f"  {name:<22} below {m['below_pct']:>3.0f}%   cover {m['cover_s']:>4.1f}s   "
          f"avg {m['avg']:>6.0f} B/s")
