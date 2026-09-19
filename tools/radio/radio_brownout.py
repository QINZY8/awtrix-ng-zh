"""Watch for brownout resets while the radio plays, and report the conditions.

A brownout reset is the device losing supply voltage, not a software fault. This
polls uptimeSeconds and resetReason so a reset is caught the moment it happens,
and records the brightness and audio state that were in force when it did.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "丹阳电台"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 180
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
    try:
        _, body = call("GET", "/api/v1/device")
        return json.loads(body)
    except Exception:  # noqa: BLE001
        return None


def audio():
    try:
        _, body = call("GET", "/api/v1/audio")
        return json.loads(body)["radio"]
    except Exception:  # noqa: BLE001
        return None


print(f"playing {NAME}, watching for brownout resets for {SECONDS}s\n")
print(call("POST", "/api/v1/audio/play", {"station": NAME}))

last_uptime = None
resets = []
start = time.time()
while time.time() - start < SECONDS:
    d = device()
    if d is None:
        print(f"t={time.time() - start:6.1f}  DEVICE UNREACHABLE")
        time.sleep(2)
        continue
    uptime = d.get("uptimeSeconds")
    reason = d.get("resetReason")
    if last_uptime is not None and uptime is not None and uptime < last_uptime:
        resets.append((time.time() - start, reason, d.get("brightness")))
        print(f"t={time.time() - start:6.1f}  *** RESET ***  reason={reason}  "
              f"brightness={d.get('brightness')}  uptime was {last_uptime}s")
    last_uptime = uptime
    r = audio()
    buf = r["bufferBytes"] if r else -1
    ur = r["underruns"] if r else -1
    print(f"t={time.time() - start:6.1f}  up={uptime:>5}s  fps={d.get('fps'):>3}  "
          f"bri={d.get('brightness'):>3}  buf={buf:>6}  ur={ur:>4}  "
          f"heap={d.get('freeHeapBytes')}")
    time.sleep(2)

call("POST", "/api/v1/audio/stop")
print(f"\nresets observed: {len(resets)}")
for t, reason, bri in resets:
    print(f"  t={t:.1f}s  reason={reason}  brightness={bri}")
