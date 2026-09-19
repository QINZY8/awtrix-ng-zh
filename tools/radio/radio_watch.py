"""Long-running watch that logs fps, buffer and underruns until a dip is caught.

The dip is intermittent: one 45 s window showed fps pinned at 23-27, the next
showed 40-42 with the same station. Sampling for longer and only printing the
interesting seconds makes the trigger visible.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "北京交通"
MINUTES = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
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


def device():
    _, body = call("GET", "/api/v1/device")
    return json.loads(body)


def audio():
    _, body = call("GET", "/api/v1/audio")
    return json.loads(body)["radio"]


print(f"playing {NAME} for {MINUTES:.0f} min, logging every second\n")
print(call("POST", "/api/v1/audio/play", {"station": NAME}))

rows = []
start = time.time()
while time.time() - start < MINUTES * 60:
    try:
        d = device()
        r = audio()
    except Exception as exc:  # noqa: BLE001
        print(f"  poll failed: {exc}")
        time.sleep(2)
        continue
    t = time.time() - start
    row = (t, d.get("fps") or 0, r["bufferBytes"], r["underruns"], r["starvedMs"],
           r["decodeUs"], d.get("freeHeapBytes"), d.get("minFreeHeapBytes"))
    rows.append(row)
    fps = row[1]
    # Print everything for the first 20 s, then only the notable seconds.
    if t < 20 or fps < 35 or row[2] < 8192:
        flag = ""
        if fps < 35:
            flag += " LOW-FPS"
        if row[2] < 8192:
            flag += " LOW-BUF"
        print(f"t={t:6.1f}  fps={fps:>3}  buf={row[2]:>6}  ur={row[3]:>4}  "
              f"starved={row[4]:>6}  decodeUs={row[5]:>5}  "
              f"heap={row[6]}/{row[7]}{flag}")
    time.sleep(1)

call("POST", "/api/v1/audio/stop")

fps_values = [r[1] for r in rows]
bufs = [r[2] for r in rows]
print(f"\n== summary over {len(rows)} samples ==")
print(f"fps      min {min(fps_values)}  median {sorted(fps_values)[len(fps_values) // 2]}  "
      f"max {max(fps_values)}")
print(f"buffer   min {min(bufs)}  max {max(bufs)}")
print(f"underruns {rows[0][3]} -> {rows[-1][3]}")
print(f"starved  {rows[0][4]} -> {rows[-1][4]} ms")
low_fps = sum(1 for f in fps_values if f < 35)
low_buf = sum(1 for b in bufs if b < 8192)
print(f"seconds with fps < 35:  {low_fps} / {len(rows)}")
print(f"seconds with buf < 8K:  {low_buf} / {len(rows)}")

# Correlate: do the low-fps seconds line up with the low-buffer seconds?
both = sum(1 for r in rows if r[1] < 35 and r[2] < 8192)
print(f"seconds with both:      {both}")
if low_fps and low_buf:
    print("\ncorrelation: low fps and low buffer happen together"
          if both > min(low_fps, low_buf) * 0.5 else
          "\ncorrelation: the two are largely independent")
