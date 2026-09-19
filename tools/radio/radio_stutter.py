"""Sample the radio counters at a fixed interval to characterise stutter.

Stutter shows up as underruns climbing and bufferBytes sawtoothing to near zero.
This samples often enough to see the shape and reports the rate of change so the
cause can be told apart:

  starvedMs climbing  -> the stream is not arriving fast enough (network/Wi-Fi)
  underruns climbing with starvedMs flat -> the decode/write path cannot keep up
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "北京交通"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 40
INTERVAL = 0.5
BASE = f"http://{HOST}"


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


print(call("POST", "/api/v1/audio/play", {"station": NAME}))

samples = []
start = time.time()
while time.time() - start < SECONDS:
    try:
        _, body = call("GET", "/api/v1/audio")
        r = json.loads(body)["radio"]
    except Exception as exc:  # noqa: BLE001
        print(f"  poll failed: {exc}")
        time.sleep(INTERVAL)
        continue
    t = time.time() - start
    samples.append((t, r["bufferBytes"], r["underruns"], r["starvedMs"], r["decodeUs"]))
    print(f"t={t:5.1f}  buf={r['bufferBytes']:>6}  ur={r['underruns']:>4}  "
          f"starved={r['starvedMs']:>6}  decodeUs={r['decodeUs']:>5}")
    time.sleep(INTERVAL)

call("POST", "/api/v1/audio/stop")

if len(samples) < 4:
    print("\nnot enough samples")
    sys.exit(1)

bufs = [s[1] for s in samples]
urs = [s[2] for s in samples]
starved = [s[3] for s in samples]
span = samples[-1][0] - samples[0][0]

print("\n== summary ==")
print(f"duration          {span:.1f} s")
print(f"buffer min/max    {min(bufs)} / {max(bufs)}")
print(f"buffer empty hits {sum(1 for b in bufs if b < 4096)}")
print(f"underruns         {urs[0]} -> {urs[-1]}  ({urs[-1] - urs[0]} in {span:.0f}s, "
      f"{(urs[-1] - urs[0]) / span * 60:.1f}/min)")
print(f"starvedMs         {starved[0]} -> {starved[-1]}  "
      f"({starved[-1] - starved[0]} ms, {(starved[-1] - starved[0]) / span * 100:.0f}% of wall time)")
print(f"decodeUs          {min(s[4] for s in samples)} - {max(s[4] for s in samples)}")

grew_starved = starved[-1] - starved[0] > span * 200   # >20% of wall time
grew_ur = urs[-1] - urs[0] > 2
if grew_starved:
    print("\nverdict: the stream is arriving too slowly -> network / Wi-Fi")
elif grew_ur:
    print("\nverdict: underruns without starvation -> decode or I2S write path")
else:
    print("\nverdict: steady, no stutter observed in this window")
