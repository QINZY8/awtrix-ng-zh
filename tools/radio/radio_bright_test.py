"""Test whether the distortion tracks the panel brightness.

The MAX98357A and the LED matrix share the 5 V rail, and a brownout reset was
already observed at brightness 200. If the crackle is supply sag rather than
amplifier gain, it should get worse as the panel draws more current - which is
what the brightness setting controls.

This plays the same station at several brightness levels and watches the audio
counters and the reset reason.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "镇江交通"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 15
BASE = f"http://{HOST}"

LEVELS = [30, 80, 130, 180, 220]


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


original = json.loads(call("GET", "/api/v1/settings")[1])
orig_bri = original.get("brightness")
orig_auto = original.get("autoBrightness")
print(f"original brightness {orig_bri} (autoBrightness {orig_auto})\n")

# Auto brightness would fight the test, so it is turned off for the duration.
call("PATCH", "/api/v1/settings", {"autoBrightness": False})
time.sleep(1)

print(f"playing {NAME} at each brightness for {SECONDS}s\n")
print(f"{'brightness':>10} {'underruns':>10} {'avgBuf':>8} {'avgFPS':>7} {'reset':>6} {'resetReason':>13}")
print("-" * 62)

for bri in LEVELS:
    call("PATCH", "/api/v1/settings", {"brightness": bri})
    time.sleep(1)
    call("POST", "/api/v1/audio/play", {"station": NAME})
    time.sleep(4)

    start_ur = audio()["underruns"]
    start_up = device().get("uptimeSeconds") or 0
    bufs = []
    fps_values = []
    reset = False
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        r = audio()
        d = device()
        if (d.get("uptimeSeconds") or 0) < start_up:
            reset = True
        bufs.append(r["bufferBytes"])
        fps_values.append(d.get("fps") or 0)
        time.sleep(1)
    ur = audio()["underruns"] - start_ur
    d = device()
    call("POST", "/api/v1/audio/stop")
    time.sleep(1)

    avg_buf = sum(bufs) / len(bufs) if bufs else 0
    avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
    print(f"{bri:>10} {ur:>10} {avg_buf:>8.0f} {avg_fps:>7.1f} "
          f"{'YES' if reset else 'no':>6} {str(d.get('resetReason')):>13}")

call("PATCH", "/api/v1/settings", {"brightness": orig_bri, "autoBrightness": orig_auto})
print(f"\nbrightness restored to {orig_bri} (autoBrightness {orig_auto})")
