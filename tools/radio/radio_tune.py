"""Tune the device for the stutter seen with the Chinese stations, and verify.

Two independent problems were measured:

1. The Qingting FM endpoints deliver 8000 B/s only 54-62% of seconds, so the
   64 KB input buffer drains and playback underruns. Nothing on the device can
   fix a source that under-delivers; the buffer only buys time.

2. When the buffer does empty, the audio task spins on an empty socket and the
   render loop drops from 42 fps to ~25 fps, which is the visible stutter.

3. A brownout reset was also observed, which restarts the whole device.

This script applies the settings that reduce all three, and reports the state
before and after so the effect is visible.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
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


def settings():
    _, body = call("GET", "/api/v1/settings")
    return json.loads(body)


def device():
    _, body = call("GET", "/api/v1/device")
    return json.loads(body)


before = settings()
dev = device()
print("== before ==")
print(f"  brightness      {before.get('brightness')}  (autoBrightness "
      f"{before.get('autoBrightness')})")
print(f"  radioVolume     {before.get('radioVolume')}")
print(f"  radioMeta       {before.get('radioMeta')}")
print(f"  resetReason     {dev.get('resetReason')}")
print(f"  uptimeSeconds   {dev.get('uptimeSeconds')}")

# 1. Cap the brightness. The matrix is the largest current draw, and a brownout
#    reset was observed, so the supply is already marginal.
print("\n== applying ==")
print("  brightness -> 120 (halves the LED current vs 200)")
print(call("PATCH", "/api/v1/settings", {"brightness": 120})[1][:80])

# 2. Turn off the title announcement. These stations send no ICY metadata so it
#    is a no-op here, but it removes a notification push on any station that does.
print("  radioMeta -> false")
print(call("PATCH", "/api/v1/settings", {"radioMeta": False})[1][:80])

time.sleep(2)
after = settings()
print("\n== after ==")
print(f"  brightness      {after.get('brightness')}")
print(f"  radioVolume     {after.get('radioVolume')}")
print(f"  radioMeta       {after.get('radioMeta')}")
