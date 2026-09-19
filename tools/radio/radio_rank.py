"""Rank the configured stations by how steadily they deliver bytes.

The stutter comes from stations that average enough bytes but dip below the
8000 B/s playback rate for whole seconds. This measures each station for a
short window and reports the share of seconds that fall below the rate, which
is what predicts audible stutter.
"""
import concurrent.futures
import socket
import sys
import time

HOST = "lhttp.qingting.fm"
NEEDED_BPS = 8000
SECONDS = 25.0
TIMEOUT = 12

STATIONS = [
    ("北京交通", "1291"), ("上海动感101", "273"), ("江苏新闻", "4930"),
    ("深圳飞扬971", "1270"), ("佛山电台", "1260"), ("无锡交通", "1152"),
    ("苏州新闻", "1153"), ("常州交通", "1154"), ("南通交通", "1155"),
    ("扬州新闻", "1156"), ("徐州交通", "1157"), ("镇江交通", "1158"),
    ("泰州交通", "1160"), ("盐城交通", "1262"), ("淮安交通", "1263"),
    ("连云港交通", "1271"), ("宿迁交通", "1272"), ("江阴电台", "1273"),
    ("宜兴电台", "1274"), ("昆山电台", "1275"), ("张家港电台", "1295"),
    ("常熟电台", "1301"), ("太仓电台", "1303"), ("吴江电台", "4900"),
    ("溧阳电台", "4901"), ("金坛电台", "4904"), ("丹阳电台", "4905"),
    ("句容电台", "4932"), ("扬中电台", "4970"),
]


def measure(item):
    name, channel = item
    path = f"/live/{channel}/64k.mp3"
    try:
        sock = socket.create_connection((HOST, 80), TIMEOUT)
    except OSError as exc:
        return name, channel, None, f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return name, channel, None, "no head"
            buf += chunk
        _, _, body = buf.partition(b"\r\n\r\n")

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
            return name, channel, None, "no samples"
        below = sum(1 for b in per_second if b < NEEDED_BPS)
        return name, channel, {
            "avg": total / span,
            "below_pct": below / len(per_second) * 100,
            "min": min(per_second),
            "samples": len(per_second),
        }, ""
    finally:
        sock.close()


def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for r in pool.map(measure, STATIONS):
            results.append(r)

    ok = [r for r in results if r[2]]
    ok.sort(key=lambda r: (r[2]["below_pct"], -r[2]["avg"]))

    print(f"{'station':<14} {'avg B/s':>8} {'below%':>7} {'min B/s':>8}  verdict")
    print("-" * 62)
    for name, channel, m, err in ok:
        if m["below_pct"] == 0:
            verdict = "STABLE"
        elif m["below_pct"] < 20:
            verdict = "mostly ok"
        elif m["below_pct"] < 50:
            verdict = "stutters"
        else:
            verdict = "UNUSABLE"
        print(f"{name:<14} {m['avg']:>8.0f} {m['below_pct']:>6.0f}% {m['min']:>8.0f}  {verdict}")

    for name, channel, m, err in results:
        if not m:
            print(f"{name:<14} {'-':>8} {'-':>7} {'-':>8}  {err[:20]}")

    stable = [r for r in ok if r[2]["below_pct"] == 0]
    print(f"\nstable stations: {len(stable)} / {len(ok)}")
    for name, channel, _, _ in stable:
        print(f'  {{"name": "{name}", "url": "http://lhttp.qingting.fm/live/{channel}/64k.mp3"}},')


if __name__ == "__main__":
    main()
