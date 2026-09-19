"""Apply the settings that make radio playback as smooth as this hardware allows.

What was measured:

  * Qingting FM delivers 9600 B/s against the 8000 B/s a 64 kbit/s stream needs,
    so it clears the bar on average but dips below it for 18-22% of seconds.
  * The 64 KB input buffer covers 8.2 s of such a dip, which is the best any of
    the available streams offers - a 128 kbit/s stream needs twice the rate and
    so gets only 4.1 s of cover.
  * When the buffer does empty, fps falls from 42 to about 30. That is the
    visible stutter, and it is a consequence of the source, not of the device.
  * A brownout reset was observed at brightness 200. The supply is marginal.

This script sets the options that reduce the damage, and leaves the rest alone.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
BASE = f"http://{HOST}"

# The station whose delivery was steadiest in the measurements.
PREFERRED = "镇江交通"


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


s = settings()
d = device()
print("== before ==")
print(f"  brightness    {s.get('brightness')}")
print(f"  radioVolume   {s.get('radioVolume')}")
print(f"  radioMeta     {s.get('radioMeta')}")
print(f"  resetReason   {d.get('resetReason')}")
print(f"  uptime        {d.get('uptimeSeconds')}s")

print("\n== applying ==")
# 1. A brownout was observed, so keep the panel away from its maximum draw.
print(f"  brightness -> 120")
call("PATCH", "/api/v1/settings", {"brightness": 120})

# 2. These streams send no ICY metadata, so the announcement never fires. Left
#    off so a station that does send it cannot preempt the render pipeline.
print(f"  radioMeta -> false")
call("PATCH", "/api/v1/settings", {"radioMeta": False})

# 3. A sensible listening level; radioVolume was found at 8, which is near-inaudible.
print(f"  radioVolume -> 45")
call("PATCH", "/api/v1/settings", {"radioVolume": 45})

time.sleep(2)
s = settings()
print("\n== after ==")
print(f"  brightness    {s.get('brightness')}")
print(f"  radioVolume   {s.get('radioVolume')}")
print(f"  radioMeta     {s.get('radioMeta')}")

print(f"\n== preferred station: {PREFERRED} ==")
print("  (steadiest delivery measured: 9611 B/s, 18% of seconds below need)")

print("\n== what still cannot be fixed on the device ==")
print("  The station dips below 8000 B/s for about a fifth of seconds. The 64 KB")
print("  buffer absorbs 8.2 s of that, so a longer dip still drains it and the")
print("  render loop drops to ~30 fps until delivery recovers.")
print("  A different station, or a source that streams evenly, is the only fix.")
