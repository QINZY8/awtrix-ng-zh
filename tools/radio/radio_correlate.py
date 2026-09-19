"""Test whether an empty input buffer is what costs render frames.

The correlation is visible in the logs but not proven: fps falls when the buffer
is low. This plays a stream that is known to hold its rate (SomaFM) and one that
does not (a Qingting station), and compares fps against buffer for both. If fps
only drops on the under-delivering stream, the buffer is the cause.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
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


def run(label, url=None, station=None):
    payload = {"url": url} if url else {"station": station}
    call("POST", "/api/v1/audio/play", payload)
    time.sleep(5)
    rows = []
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        r = audio()
        d = device()
        rows.append((r["bufferBytes"], d.get("fps") or 0, r["underruns"]))
        time.sleep(1)
    call("POST", "/api/v1/audio/stop")
    time.sleep(1)

    if not rows:
        print(f"{label}: no samples")
        return
    # Split the samples by whether the buffer was healthy.
    healthy = [f for b, f, _ in rows if b > 16384]
    starved = [f for b, f, _ in rows if b <= 16384]
    print(f"\n{label}")
    print(f"  samples            {len(rows)}")
    print(f"  buffer > 16 KB     {len(healthy):>3} samples, "
          f"fps {sum(healthy) / len(healthy):.1f}" if healthy else "  buffer > 16 KB      0")
    print(f"  buffer <= 16 KB    {len(starved):>3} samples, "
          f"fps {sum(starved) / len(starved):.1f}" if starved else "  buffer <= 16 KB     0")
    if healthy and starved:
        drop = sum(healthy) / len(healthy) - sum(starved) / len(starved)
        print(f"  fps drop when low  {drop:.1f}")
    print(f"  underruns          {rows[-1][2] - rows[0][2]}")


print(f"comparing a stable stream against an under-delivering one, {SECONDS}s each")
run("SomaFM (delivers 15308 B/s, 0% below need)", url="http://ice1.somafm.com/groovesalad-128-mp3")
run("南通交通 (delivers 9636 B/s, 18% below need)", station="南通交通")
