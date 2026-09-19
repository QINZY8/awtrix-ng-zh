"""Play each candidate on the device and count the audible breaks.

Server-side measurements predict stutter but do not prove it, because the device
has its own 64 KB buffer and its own reconnect behaviour. This plays each station
for a fixed time and counts underruns, which is what is actually heard.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 30
BASE = f"http://{HOST}"

CANDIDATES = [
    "镇江交通", "南通交通", "扬州新闻", "淮安交通", "丹阳电台",
    "徐州交通", "宿迁交通", "深圳飞扬971", "苏州新闻", "吴江电台",
]


def call(method, path, payload=None, timeout=20):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def audio():
    _, body = call("GET", "/api/v1/audio")
    return json.loads(body)["radio"]


def device():
    _, body = call("GET", "/api/v1/device")
    return json.loads(body)


print(f"each station plays {SECONDS}s; underruns and low-fps seconds are counted\n")
print(f"{'station':<14} {'underruns':>10} {'lowFPS':>7} {'minBuf':>8} {'avgFPS':>7}")
print("-" * 52)

rows = []
for name in CANDIDATES:
    call("POST", "/api/v1/audio/play", {"station": name})
    time.sleep(3)                       # let it connect and preroll
    start_ur = audio()["underruns"]
    min_buf = 1 << 30
    fps_values = []
    low_fps = 0
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        r = audio()
        d = device()
        min_buf = min(min_buf, r["bufferBytes"])
        fps = d.get("fps") or 0
        fps_values.append(fps)
        if fps < 35:
            low_fps += 1
        time.sleep(1)
    end_ur = audio()["underruns"]
    call("POST", "/api/v1/audio/stop")
    time.sleep(1)

    avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
    ur = end_ur - start_ur
    rows.append((name, ur, low_fps, min_buf, avg_fps))
    print(f"{name:<14} {ur:>10} {low_fps:>7} {min_buf:>8} {avg_fps:>7.1f}")

print("\n== ranked by underruns, then low-fps seconds ==")
for name, ur, low_fps, min_buf, avg_fps in sorted(rows, key=lambda r: (r[1], r[2])):
    print(f"  {name:<14} ur={ur:>3}  lowFPS={low_fps:>3}  minBuf={min_buf:>6}  "
          f"avgFPS={avg_fps:.1f}")
