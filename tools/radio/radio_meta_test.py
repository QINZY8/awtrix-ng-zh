"""Test whether the radio metadata announcement is what costs frames.

When radioMeta is on, every ICY title change pushes a notification onto the
matrix, which preempts the normal render pipeline. These streams do not send
ICY metadata, so the setting should cost nothing here - which is itself worth
confirming before blaming it.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "丹阳电台"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 30
BASE = f"http://{HOST}"


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


def device():
    _, body = call("GET", "/api/v1/device")
    return json.loads(body)


def audio():
    _, body = call("GET", "/api/v1/audio")
    return json.loads(body)["radio"]


def run(label):
    call("POST", "/api/v1/audio/play", {"station": NAME})
    time.sleep(4)
    fps_values = []
    min_buf = 1 << 30
    start_ur = audio()["underruns"]
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        min_buf = min(min_buf, audio()["bufferBytes"])
        fps_values.append(device().get("fps") or 0)
        time.sleep(1)
    ur = audio()["underruns"] - start_ur
    call("POST", "/api/v1/audio/stop")
    time.sleep(1)
    avg = sum(fps_values) / len(fps_values) if fps_values else 0
    low = sum(1 for f in fps_values if f < 35)
    print(f"{label:<22} avgFPS={avg:5.1f}  minFPS={min(fps_values):>3}  "
          f"lowFPS={low:>2}  underruns={ur:>3}  minBuf={min_buf:>6}")
    return avg, low, ur


print(f"station {NAME}, {SECONDS}s per run\n")
run("radioMeta=on")

print(call("PATCH", "/api/v1/settings", {"radioMeta": False}))
time.sleep(2)
run("radioMeta=off")

print(call("PATCH", "/api/v1/settings", {"radioMeta": True}))
print("\nradioMeta restored to on")
