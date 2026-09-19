"""Test whether the distortion tracks the software volume setting.

If the crackle is digital clipping, lowering radioVolume fixes it, because the
gain is applied to the PCM before I2S and any sample that would overflow is
scaled down first. If the crackle is the amplifier or speaker being driven too
hard, lowering radioVolume also helps but only because it reduces the signal
reaching the amplifier - and the same effect is available by lowering the
MAX98357A's own GAIN pin, without losing digital resolution.

This plays the same station at several volumes and reports the audio counters,
so a volume that is too high shows up as a different failure than one that is
merely loud.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "镇江交通"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 12
BASE = f"http://{HOST}"

VOLUMES = [20, 40, 60, 80, 100]


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


original = json.loads(call("GET", "/api/v1/settings")[1]).get("radioVolume")
print(f"original radioVolume: {original}\n")
print(f"playing {NAME} at each volume for {SECONDS}s\n")
print(f"{'volume':>7} {'underruns':>10} {'avgBuf':>8} {'minBuf':>8} {'avgFPS':>7} {'reset':>6}")
print("-" * 54)

for vol in VOLUMES:
    call("PATCH", "/api/v1/settings", {"radioVolume": vol})
    time.sleep(1)
    call("POST", "/api/v1/audio/play", {"station": NAME})
    time.sleep(4)

    start_ur = audio()["underruns"]
    start_up = device().get("uptimeSeconds")
    bufs = []
    fps_values = []
    reset = False
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        r = audio()
        d = device()
        if d.get("uptimeSeconds", 0) < (start_up or 0):
            reset = True
        bufs.append(r["bufferBytes"])
        fps_values.append(d.get("fps") or 0)
        time.sleep(1)
    ur = audio()["underruns"] - start_ur
    call("POST", "/api/v1/audio/stop")
    time.sleep(1)

    avg_buf = sum(bufs) / len(bufs) if bufs else 0
    avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
    print(f"{vol:>7} {ur:>10} {avg_buf:>8.0f} {min(bufs) if bufs else 0:>8} "
          f"{avg_fps:>7.1f} {'YES' if reset else 'no':>6}")

call("PATCH", "/api/v1/settings", {"radioVolume": original})
print(f"\nradioVolume restored to {original}")
