"""Check the channel count of the streams, and what the I2S config does with it.

A mono MP3 decoded into an interleaved buffer, then handed to I2S configured as
ONLY_LEFT, is a known source of distortion: the driver expects one channel of
data but the buffer holds one sample per frame, and any mismatch between what
the decoder wrote and what the driver reads shifts every sample.

This reports the channel count of the configured stations, which is the input to
that decision.
"""
import socket
import sys
from collections import Counter

HOST = "lhttp.qingting.fm"
TIMEOUT = 10

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
RATES = [44100, 48000, 32000, 0]
CHANNEL_MODES = ["stereo", "joint stereo", "dual channel", "mono"]

STATIONS = [
    ("镇江交通", "1158"), ("南通交通", "1155"), ("扬州新闻", "1156"),
    ("淮安交通", "1263"), ("丹阳电台", "4905"), ("深圳飞扬971", "1270"),
    ("苏州新闻", "1153"), ("北京交通", "1291"), ("上海动感101", "273"),
]


def probe(channel):
    path = f"/live/{channel}/64k.mp3"
    try:
        sock = socket.create_connection((HOST, 80), TIMEOUT)
    except OSError as exc:
        return None, f"connect: {exc}"
    sock.settimeout(TIMEOUT)
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 0\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return None, "no head"
            buf += chunk
        _, _, data = buf.partition(b"\r\n\r\n")
        # One more read is enough for a few frames.
        try:
            data += sock.recv(16384)
        except socket.timeout:
            pass
    finally:
        sock.close()

    modes = Counter()
    rates = Counter()
    i = 0
    n = len(data)
    while i + 4 <= n and sum(modes.values()) < 40:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            h = data[i + 1]
            if ((h >> 3) & 0x03) == 3 and ((h >> 1) & 0x03) == 1:
                h2 = data[i + 2]
                h3 = data[i + 3]
                br = BITRATES[(h2 >> 4) & 0x0F]
                sr = RATES[(h2 >> 2) & 0x03]
                mode = (h3 >> 6) & 0x03
                if br and sr:
                    pad = (h2 >> 1) & 0x01
                    modes[CHANNEL_MODES[mode]] += 1
                    rates[sr] += 1
                    i += int(144 * br * 1000 / sr) + pad
                    continue
        i += 1
    return (dict(modes), dict(rates)), ""


print(f"{'station':<14} {'channel mode':<16} {'sample rate'}")
print("-" * 48)
for name, ch in STATIONS:
    result, err = probe(ch)
    if not result:
        print(f"{name:<14} {'-':<16} {err[:20]}")
        continue
    modes, rates = result
    mode_str = ", ".join(f"{k} x{v}" for k, v in modes.items())
    rate_str = ", ".join(f"{k} Hz x{v}" for k, v in rates.items())
    print(f"{name:<14} {mode_str:<16} {rate_str}")

print("\n== why this matters ==")
print("AudioOutEsp32.cpp configures I2S as:")
print("  channels == 1  ->  I2S_CHANNEL_FMT_ONLY_LEFT")
print("  channels == 2  ->  I2S_CHANNEL_FMT_RIGHT_LEFT")
print()
print("ONLY_LEFT means the driver takes one 16-bit sample per frame from the")
print("buffer. The decoder writes 'samples * channels' int16 values. For a mono")
print("stream those agree, so the config is right - but it is worth confirming")
print("the streams really are mono before looking elsewhere.")
