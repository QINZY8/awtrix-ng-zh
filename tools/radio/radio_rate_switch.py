"""Test whether the distortion depends on the stream's sample rate.

The stations differ in sample rate (32 kHz, 44.1 kHz, 48 kHz) and the I2S
driver is reinstalled every time it changes, because AudioOutEsp32.cpp compares
the incoming rate against the running one and reconfigure when they differ.

A stream that changes rate mid-playback forces repeated driver reinstall, and
each reinstall is an audible break. This checks whether any station switches
rate within a single connection, which would be a real fault rather than a
property of the source.
"""
import socket
import sys
import time
from collections import Counter

HOST = "lhttp.qingting.fm"
TIMEOUT = 12
SECONDS = 30.0

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
RATES = [44100, 48000, 32000, 0]

STATIONS = [
    ("镇江交通", "1158", 32000),
    ("南通交通", "1155", 48000),
    ("深圳飞扬971", "1270", 44100),
    ("北京交通", "1291", 32000),
]


def scan(channel, seconds=SECONDS):
    path = f"/live/{channel}/64k.mp3"
    sock = socket.create_connection((HOST, 80), TIMEOUT)
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

        start = time.time()
        while time.time() - start < seconds:
            try:
                chunk = sock.recv(16384)
            except socket.timeout:
                continue
            if not chunk:
                break
            data += chunk
    finally:
        sock.close()

    rates = Counter()
    modes = Counter()
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
                    rates[sr] += 1
                    modes[(data[i + 3] >> 6) & 0x03] += 1
                    i += int(144 * br * 1000 / sr) + pad
                    continue
        i += 1
    return (dict(rates), dict(modes), len(data)), ""


print(f"{'station':<14} {'expected':>9} {'observed':<28} {'frames':>7} {'switches':>9}")
print("-" * 74)
for name, ch, expect in STATIONS:
    result, err = scan(ch)
    if not result:
        print(f"{name:<14} {expect:>9} {err[:28]}")
        continue
    rates, modes, size = result
    observed = ", ".join(f"{k}Hz x{v}" for k, v in sorted(rates.items()))
    switches = "NO" if len(rates) == 1 else f"YES ({len(rates)} rates)"
    print(f"{name:<14} {expect:>9} {observed:<28} {sum(rates.values()):>7} {switches:>9}")

print("\n== what this means ==")
print("If every station keeps one sample rate for the whole connection, the I2S")
print("driver is installed once per tune-in and never reinstalled mid-stream,")
print("so the rate is not the source of the distortion.")
print()
print("The rates do differ between stations (32k / 44.1k / 48k), so switching")
print("station does reinstall the driver once - that is a single click, not a")
print("continuous crackle.")
