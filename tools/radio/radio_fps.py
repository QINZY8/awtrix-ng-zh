"""Sample the device's own FPS and audio counters together while the radio plays.

The stutter is reported as audible *and* visible, which means the render loop is
losing time, not just the audio path. The device publishes `fps` in its state, so
sampling fps next to the radio counters shows whether the two move together.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "北京交通"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 40
BASE = f"http://{HOST}"


def call(method, path, payload=None, timeout=15):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def state():
    _, body = call("GET", "/api/v1/device")
    return json.loads(body)


print("== idle baseline (no radio) ==")
for _ in range(4):
    time.sleep(2)
    s = state()
    print(f"  fps={s.get('fps')}  freeHeap={s.get('freeHeapBytes')}  "
          f"minFreeHeap={s.get('minFreeHeapBytes')}")

print(f"\n== playing {NAME} ==")
print(call("POST", "/api/v1/audio/play", {"station": NAME}))

fps_values = []
ur_values = []
start = time.time()
while time.time() - start < SECONDS:
    try:
        s = state()
        _, abody = call("GET", "/api/v1/audio")
        r = json.loads(abody)["radio"]
    except Exception as exc:  # noqa: BLE001
        print(f"  poll failed: {exc}")
        time.sleep(1)
        continue
    fps = s.get("fps") or 0
    fps_values.append(fps)
    ur_values.append(r["underruns"])
    t = time.time() - start
    print(f"t={t:5.1f}  fps={fps:>3}  buf={r['bufferBytes']:>6}  ur={r['underruns']:>4}  "
          f"starved={r['starvedMs']:>6}  decodeUs={r['decodeUs']:>5}  "
          f"heap={s.get('freeHeapBytes')}")
    time.sleep(1)

call("POST", "/api/v1/audio/stop")

if fps_values:
    print("\n== summary ==")
    print(f"fps  min {min(fps_values)}  median {sorted(fps_values)[len(fps_values) // 2]}  "
          f"max {max(fps_values)}")
    print(f"underruns {ur_values[0]} -> {ur_values[-1]}")
    target = 1000 // 24
    low = sum(1 for f in fps_values if f < target)
    print(f"seconds below the {target} fps target: {low} / {len(fps_values)}")
