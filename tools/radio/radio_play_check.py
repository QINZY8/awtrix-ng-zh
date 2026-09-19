"""Play a station on the device and watch the counters for a few seconds."""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "北京交通"
BASE = f"http://{HOST}"


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


print(call("POST", "/api/v1/audio/play", {"station": NAME}))
for i in range(8):
    time.sleep(2)
    _, body = call("GET", "/api/v1/audio")
    r = json.loads(body)["radio"]
    print(f"t={2 * (i + 1):>2}s playing={r['playing']} station={r['station']!r} "
          f"title={r['title'][:32]!r} err={r['error'][:30]!r} "
          f"buf={r['bufferBytes']:>6} underruns={r['underruns']} "
          f"decodeUs={r['decodeUs']}")
