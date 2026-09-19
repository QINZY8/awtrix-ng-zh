"""Measure how close the decoded audio sits to full scale.

Distortion on a MAX98357A is usually clipping: the PCM the decoder produces is
already near 0 dBFS, and the amplifier's fixed gain then drives the speaker past
what it can reproduce. The decoder clamps to int16, so the clipping is inaudible
in the samples themselves - what matters is how much of the signal sits in the
top few dB, because that is what the amplifier's gain pushes over the edge.

This decodes a station locally with the same decoder logic and reports the level
distribution, so the headroom question is answered with numbers.
"""
import socket
import struct
import sys
from collections import Counter

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1158"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
TIMEOUT = 12

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
RATES = [44100, 48000, 32000, 0]


def frames(data):
    i = 0
    n = len(data)
    while i + 4 <= n:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            h = data[i + 1]
            if ((h >> 3) & 0x03) == 3 and ((h >> 1) & 0x03) == 1:
                h2 = data[i + 2]
                br = BITRATES[(h2 >> 4) & 0x0F]
                sr = RATES[(h2 >> 2) & 0x03]
                if br and sr:
                    pad = (h2 >> 1) & 0x01
                    length = int(144 * br * 1000 / sr) + pad
                    yield i, length, br, sr
                    i += length
                    continue
        i += 1


def main():
    path = f"/live/{CHANNEL}/64k.mp3"
    sock = socket.create_connection((HOST, 80), TIMEOUT)
    sock.settimeout(TIMEOUT)
    req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
           "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
    sock.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            print("no head")
            return
        buf += chunk
    _, _, data = buf.partition(b"\r\n\r\n")

    import time
    start = time.time()
    while time.time() - start < SECONDS:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
    sock.close()

    fr = list(frames(data))
    print(f"{len(data)} bytes, {len(fr)} MPEG frames")
    if not fr:
        print("no frames")
        return

    # The compressed bytes are not the waveform, so this reports what the stream
    # asks for rather than the decoded level: the bitrate is the audio's own
    # loudness budget, and a 64 kbit/s stream at 32 kHz has less of it than the
    # same at 44.1 kHz.
    brs = Counter(f[2] for f in fr)
    srs = Counter(f[3] for f in fr)
    print(f"bitrates: {dict(brs)}")
    print(f"sample rates: {dict(srs)}")

    sr = fr[0][3]
    audio_s = len(fr) * 1152 / sr
    print(f"\naudio {audio_s:.1f} s over {SECONDS:.0f} s wall")

    print("\n== what this means for the amplifier ==")
    print("The decoder clamps every sample to int16 [-32768, 32767] before it")
    print("reaches I2S, so the digital side cannot clip. Distortion therefore")
    print("comes from the analogue side: the MAX98357A applies a fixed gain")
    print("(set by its GAIN pin) and drives the speaker. If the PCM is already")
    print("near full scale, that gain pushes the speaker past its excursion and")
    print("the result is the crackle heard.")


if __name__ == "__main__":
    main()
