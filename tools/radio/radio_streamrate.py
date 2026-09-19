"""Check whether the stream itself contains gaps in the audio data.

The device's input buffer keeps draining to zero even though the network is
delivering bytes steadily. That points at the stream, not the network: if the
source inserts silence or repeats data, the decoder may consume more than the
nominal bitrate implies.

This decodes the stream and reports the bitrate of every MPEG frame, so a
stretch of unusually small frames (silence) or a burst of large ones is visible.
"""
import socket
import sys
from collections import Counter

HOST = "lhttp.qingting.fm"
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else "1291"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
TIMEOUT = 12

# MPEG-1 Layer III bitrate table, kbit/s, indexed by the 4-bit field.
BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
RATES = [44100, 48000, 32000, 0]


def find_frames(data):
    """Yield (offset, bitrate, samplerate, frame_len) for each MPEG-1 Layer III frame."""
    i = 0
    n = len(data)
    while i + 4 <= n:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            h = data[i + 1]
            version = (h >> 3) & 0x03      # 3 = MPEG-1
            layer = (h >> 1) & 0x03        # 1 = Layer III
            if version == 3 and layer == 1:
                h2 = data[i + 2]
                br_idx = (h2 >> 4) & 0x0F
                sr_idx = (h2 >> 2) & 0x03
                br = BITRATES[br_idx]
                sr = RATES[sr_idx]
                if br and sr:
                    pad = (h2 >> 1) & 0x01
                    length = int(144 * br * 1000 / sr) + pad
                    yield i, br, sr, length
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

    frames = list(find_frames(data))
    print(f"captured {len(data)} bytes, found {len(frames)} MPEG-1 Layer III frames\n")
    if not frames:
        print("no frames found - not MPEG-1 Layer III")
        return

    brs = Counter(f[1] for f in frames)
    print("bitrate distribution:")
    for br, count in sorted(brs.items()):
        print(f"  {br:>4} kbit/s  {count:>6} frames  {count / len(frames) * 100:5.1f}%")

    rates = Counter(f[2] for f in frames)
    print(f"sample rates: {dict(rates)}")

    # Frames per second of audio: each frame is 1152 samples.
    sr = frames[0][2]
    audio_seconds = len(frames) * 1152 / sr
    print(f"\naudio duration  {audio_seconds:.1f} s")
    print(f"wall duration   {SECONDS:.1f} s")
    print(f"ratio           {audio_seconds / SECONDS:.3f}  "
          f"({'OK' if audio_seconds / SECONDS > 0.98 else 'AUDIO IS SHORTER THAN WALL TIME'})")

    # The device consumes audio at exactly 1.0x wall time. If the stream carries
    # less audio than wall time, the buffer can only drain.
    if audio_seconds / SECONDS < 0.98:
        print("\nverdict: the stream does not carry enough audio for real-time playback")
    else:
        print("\nverdict: the stream carries enough audio; the gap is elsewhere")


if __name__ == "__main__":
    main()
