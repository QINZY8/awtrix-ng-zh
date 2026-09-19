"""Show why a 32 kHz stream over-delivers against a 44.1 kHz playback rate.

The stream is 64 kbit/s at 32 kHz. The device's decoder hands frames to I2S at
whatever rate the frame declares, so this is not itself a mismatch - but it does
mean the byte budget per second of audio is different from what a 44.1 kHz
stream would need, and it makes the buffer drain rate easy to misjudge.

This prints the numbers both ways so the arithmetic is not guessed at.
"""
BITRATE_KBIT = 64
FRAME_SAMPLES = 1152

for sr in (32000, 44100, 48000):
    frames_per_sec = sr / FRAME_SAMPLES
    bytes_per_frame = BITRATE_KBIT * 1000 / 8 / frames_per_sec
    bytes_per_sec = BITRATE_KBIT * 1000 / 8
    print(f"{sr:>5} Hz: {frames_per_sec:6.1f} frames/s, "
          f"{bytes_per_frame:6.1f} bytes/frame, {bytes_per_sec:7.0f} bytes/s")

print()
print("A 64 kbit/s stream always delivers 8000 bytes/s of compressed data, no")
print("matter the sample rate. The decoder turns those bytes into PCM at the")
print("stream's own rate, so playback consumes exactly 8000 bytes/s too.")
print()
print("The device holds 64 KB = 65536 bytes, i.e. 8.2 s of stream at 8000 B/s.")
print("It drains to zero only if delivery falls below 8000 B/s for that long.")
