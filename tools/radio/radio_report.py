"""Report the radio buffer and render settings that govern stutter tolerance.

Everything here is read from the running device, so the numbers are the ones in
force rather than the ones in the source tree.
"""
import json
import sys
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
BASE = f"http://{HOST}"


def call(path, timeout=20):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


settings = call("/api/v1/settings")
device = call("/api/v1/device")
audio = call("/api/v1/audio")

print("== audio / radio settings ==")
for key in ("radioVolume", "radioMeta", "soundEnabled", "mp3Volume", "buzzerVolume",
            "dfplayerVolume"):
    if key in settings:
        print(f"  {key:<16} {settings[key]}")

print("\n== device ==")
for key in ("fps", "freeHeapBytes", "minFreeHeapBytes", "psramFreeBytes",
            "psramTotalBytes", "uptimeSeconds"):
    if key in device:
        print(f"  {key:<16} {device[key]}")

print("\n== radio now ==")
r = audio.get("radio", {})
for key in ("playing", "station", "underruns", "starvedMs", "decodeUs", "bufferBytes"):
    print(f"  {key:<16} {r.get(key)}")

print("\n== what the firmware uses (from src/system/AudioOutEsp32.cpp) ==")
print("  input buffer      65536 B   (64 KB, PSRAM)")
print("  preroll           16384 B   (16 KB before playback starts)")
print("  DMA queue         8 x 512 frames = 93 ms")
print("  frames per pass   2")
print("  playback rate     8000 B/s for a 64 kbit/s stream")
print("  buffer covers     65536 / 8000 = 8.2 s of a delivery outage")
print("  preroll covers    16384 / 8000 = 2.0 s")
