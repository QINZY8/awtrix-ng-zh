"""Report station names that contain characters the device may not round-trip."""
import json
import sys
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
with urllib.request.urlopen(f"http://{HOST}/api/v1/audio", timeout=20) as r:
    data = json.loads(r.read().decode())

bad = 0
for i, st in enumerate(data["stations"]):
    name = st["name"]
    if " " in name or "\u3000" in name:
        print(f"{i:>2}  {name!r}   <- contains a space")
        bad += 1
print(f"\n{len(data['stations'])} stations, {bad} with a suspicious space")
