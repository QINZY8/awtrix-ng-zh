"""Work out whether the decode loop can keep up, from the numbers the device reports.

The audio task decodes at most kFramesPerPass MPEG frames per pass and then
blocks in i2s_write until the DMA queue has room. That is a deliberate design:
i2s_write paces the loop to real time, so the loop should run at exactly the
playback rate. If it does not, either the pass is doing too little work per
blocking call, or something else is stealing CPU.

This script does the arithmetic from observed values rather than guessing.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
NAME = sys.argv[2] if len(sys.argv) > 2 else "北京交通"
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 30
BASE = f"http://{HOST}"

# From src/system/AudioOutEsp32.cpp
DMA_BUFFER_COUNT = 8
DMA_BUFFER_FRAMES = 512
FRAMES_PER_PASS = 2
PREROLL_BYTES = 16 * 1024
INPUT_BUFFER_BYTES = 64 * 1024
SAMPLE_RATE = 44100
MP3_FRAME_SAMPLES = 1152


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


print("== the arithmetic ==")
dma_ms = DMA_BUFFER_COUNT * DMA_BUFFER_FRAMES * 1000 / SAMPLE_RATE
frame_ms = MP3_FRAME_SAMPLES * 1000 / SAMPLE_RATE
print(f"DMA queue holds      {dma_ms:.0f} ms of audio "
      f"({DMA_BUFFER_COUNT} x {DMA_BUFFER_FRAMES} frames)")
print(f"one MP3 frame is     {frame_ms:.1f} ms of audio")
print(f"a pass hands over    {FRAMES_PER_PASS} frames = {FRAMES_PER_PASS * frame_ms:.1f} ms")
print(f"i2s_write blocks for at most {dma_ms:.0f} ms before the queue has room")
print(f"preroll              {PREROLL_BYTES / 1024:.0f} KB "
      f"(~{PREROLL_BYTES / (64 * 1000 / 8) :.1f} s at 64 kbit/s)")
print(f"input buffer         {INPUT_BUFFER_BYTES / 1024:.0f} KB "
      f"(~{INPUT_BUFFER_BYTES / (64 * 1000 / 8):.1f} s at 64 kbit/s)")

print(f"\n== sampling while {NAME} plays ==")
print(call("POST", "/api/v1/audio/play", {"station": NAME}))

rows = []
start = time.time()
while time.time() - start < SECONDS:
    d = device()
    r = audio()
    rows.append((time.time() - start, d.get("fps"), r["bufferBytes"], r["underruns"],
                 r["starvedMs"], r["decodeUs"], d.get("freeHeapBytes")))
    time.sleep(1)

call("POST", "/api/v1/audio/stop")

for t, fps, buf, ur, st, du, heap in rows:
    print(f"t={t:5.1f}  fps={fps:>3}  buf={buf:>6}  ur={ur:>4}  starved={st:>6}  "
          f"decodeUs={du:>5}  heap={heap}")

if rows:
    fps = [r[1] for r in rows if r[1]]
    bufs = [r[2] for r in rows]
    print(f"\nfps    min {min(fps)}  median {sorted(fps)[len(fps) // 2]}  max {max(fps)}")
    print(f"buffer min {min(bufs)}  max {max(bufs)}")
    print(f"empty-buffer samples: {sum(1 for b in bufs if b < 4096)} / {len(bufs)}")

    # The audio task must deliver 1000/frame_ms frames per second, i.e. one pass
    # every FRAMES_PER_PASS * frame_ms. The render loop should be unaffected
    # because it is on the other core.
    print(f"\nneeded pass rate: {1000 / (FRAMES_PER_PASS * frame_ms):.1f} passes/s")
    print(f"render target:    {1000 / 24:.1f} fps")
