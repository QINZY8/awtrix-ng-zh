"""Summarise where the distortion can and cannot come from, from the code.

Everything the device does to the audio before it reaches the amplifier is in
AudioOutEsp32.cpp and Mp3Decoder.cpp. This walks that path and marks each stage
as able or unable to introduce the crackle, so the remaining candidates are
clear.
"""
print("== the signal path, stage by stage ==\n")

stages = [
    ("MP3 decode",
     "Mp3Decoder::synthesise() scales to int16 and clamps to [-32768, 32767]",
     "cannot clip: every sample is already clamped"),
    ("Volume gain",
     "AudioOutEsp32::writeDecodedFrame() multiplies by gain/100, and only when gain < 100",
     "cannot clip: the gain is an attenuation, applied in int32 before the cast"),
    ("I2S framing",
     "16-bit samples, I2S_CHANNEL_FMT_RIGHT_LEFT for stereo",
     "matches the decoder's interleaved output"),
    ("DMA queue",
     "8 buffers x 512 frames, i2s_write blocks until there is room",
     "a starved queue repeats its last descriptor, which is a gap, not a crackle"),
    ("Amplifier",
     "MAX98357A, fixed gain set by its GAIN pin, drives a 4-8 ohm speaker",
     "CAN distort: this is the only stage with gain"),
    ("Power supply",
     "5 V rail shared with the LED matrix",
     "CAN distort: a sagging rail clips the amplifier's output"),
]

for i, (name, what, verdict) in enumerate(stages, 1):
    print(f"{i}. {name}")
    print(f"   {what}")
    print(f"   -> {verdict}\n")

print("== conclusion ==")
print("The digital path cannot clip: the decoder clamps, and the volume control")
print("only ever attenuates. A crackle therefore comes from the analogue side.")
print()
print("The two analogue causes are distinguishable by their symptoms:")
print()
print("  * Amplifier gain too high for the speaker")
print("      - constant, tracks the music's loudness")
print("      - worst on bass-heavy passages")
print("      - fixed by the MAX98357A GAIN pin, or by a speaker that takes more power")
print()
print("  * Supply sag under load")
print("      - appears in bursts, often with the panel lit")
print("      - can accompany a brownout reset")
print("      - fixed by a bigger supply, and by decoupling at the amplifier")
print()
print("== the MAX98357A GAIN pin ==")
print("The breakout sets its gain by strapping GAIN to one of four levels:")
print()
print("  GAIN -> GND        3 dB    (quietest)")
print("  GAIN -> floating   9 dB    (default on most breakouts)")
print("  GAIN -> VDD       12 dB")
print("  GAIN -> VDD via 100k  15 dB  (loudest)")
print()
print("If the crackle tracks the music, moving GAIN towards GND is the fix, and")
print("it costs nothing: the digital volume stays where it is, so no resolution")
print("is lost.")
