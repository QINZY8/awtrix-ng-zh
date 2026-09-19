"""Read the device's reset reason and crash counters.

A reboot during radio playback is the real cause of the visible stutter: the
matrix goes dark and the audio stops for the whole boot sequence. The reset
reason says whether it was a panic, a watchdog, a brownout, or a deliberate
restart.
"""
import json
import sys
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
BASE = f"http://{HOST}"


def get(path, timeout=20):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


device = get("/api/v1/device")
print("== device facts ==")
for key in sorted(device):
    value = device[key]
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    print(f"  {key:<24} {value}")

print("\n== looking for reset / crash fields ==")
for key in ("resetReason", "reset_reason", "crashCount", "crash", "lastCrash",
            "resetCount", "bootCount", "panicReason", "brownout"):
    if key in device:
        print(f"  {key:<24} {device[key]}")
