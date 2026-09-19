# Radio stream tools

Helper scripts for finding and setting up internet radio stations on an AWTRIX
device. AWTRIX plays **MP3 streams only** - a URL that answers with
`Content-Type: audio/mpeg` (or Icecast/Shoutcast `icy-*` headers). HLS playlists
(`.m3u8`, `Content-Type: application/vnd.apple.mpegurl`) are **not** supported:
their segments are MPEG-TS/AAC, which the on-device MP3 decoder cannot read, and
they use relative segment paths that the playlist parser skips.

## Check a URL before using it

```powershell
python tools/radio/radio_probe.py
```

`radio_probe.py` probes a built-in candidate list and prints a verdict per URL:

| Verdict | Meaning |
|---|---|
| `OK-MP3` | usable - `audio/mpeg` or `icy-*` headers present |
| `HLS` | not usable - HLS playlist |
| `HTTP` | not usable - non-200 status |
| `OTHER` | not usable - some other content type |
| `UNREACHABLE` / `ERROR` | network problem |

`radio_probe_cn.py` does the same for a wider list of Chinese stations.

Rule of thumb: `curl -I <url>` must show `Content-Type: audio/mpeg`.

## Verify on the device

`radio_verify.py` writes a station list and plays each entry, judging success by
the device's own counters (`bufferBytes` climbing past ~20 KB, or a title
appearing):

```powershell
python tools/radio/radio_verify.py 192.168.5.16
```

`radio_play_check.py` plays one station and prints the counters every two
seconds:

```powershell
python tools/radio/radio_play_check.py 192.168.5.16 北京交通
```

## Write the final list

```powershell
python tools/radio/radio_set_cn.py 192.168.5.16
```

## Chinese stations known to work

All of these answer with `audio/mpeg` and were confirmed to buffer and play on
an ESP32-S3 device. They are Qingting FM (蜻蜓FM) Icecast endpoints; the channel
id is the only variable.

| Station | URL |
|---|---|
| 北京交通 | `http://lhttp.qingting.fm/live/1291/64k.mp3` |
| 上海动感101 | `http://lhttp.qingting.fm/live/273/64k.mp3` |
| 江苏新闻 | `http://lhttp.qingting.fm/live/4930/64k.mp3` |
| 深圳飞扬971 | `http://lhttp.qingting.fm/live/1270/64k.mp3` |
| 佛山电台 | `http://lhttp.qingting.fm/live/1260/64k.mp3` |
| 无锡交通 | `http://lhttp.qingting.fm/live/1152/64k.mp3` |
| 苏州新闻 | `http://lhttp.qingting.fm/live/1153/64k.mp3` |
| 常州交通 | `http://lhttp.qingting.fm/live/1154/64k.mp3` |
| 南通交通 | `http://lhttp.qingting.fm/live/1155/64k.mp3` |
| 扬州新闻 | `http://lhttp.qingting.fm/live/1156/64k.mp3` |
| 徐州交通 | `http://lhttp.qingting.fm/live/1157/64k.mp3` |
| 镇江交通 | `http://lhttp.qingting.fm/live/1158/64k.mp3` |
| 泰州交通 | `http://lhttp.qingting.fm/live/1160/64k.mp3` |
| 盐城交通 | `http://lhttp.qingting.fm/live/1262/64k.mp3` |
| 淮安交通 | `http://lhttp.qingting.fm/live/1263/64k.mp3` |
| 连云港交通 | `http://lhttp.qingting.fm/live/1271/64k.mp3` |
| 宿迁交通 | `http://lhttp.qingting.fm/live/1272/64k.mp3` |
| 江阴电台 | `http://lhttp.qingting.fm/live/1273/64k.mp3` |
| 宜兴电台 | `http://lhttp.qingting.fm/live/1274/64k.mp3` |
| 昆山电台 | `http://lhttp.qingting.fm/live/1275/64k.mp3` |
| 张家港电台 | `http://lhttp.qingting.fm/live/1295/64k.mp3` |
| 常熟电台 | `http://lhttp.qingting.fm/live/1301/64k.mp3` |
| 太仓电台 | `http://lhttp.qingting.fm/live/1303/64k.mp3` |
| 吴江电台 | `http://lhttp.qingting.fm/live/4900/64k.mp3` |
| 溧阳电台 | `http://lhttp.qingting.fm/live/4901/64k.mp3` |
| 金坛电台 | `http://lhttp.qingting.fm/live/4904/64k.mp3` |
| 丹阳电台 | `http://lhttp.qingting.fm/live/4905/64k.mp3` |
| 句容电台 | `http://lhttp.qingting.fm/live/4932/64k.mp3` |
| 扬中电台 | `http://lhttp.qingting.fm/live/4970/64k.mp3` |

International fallbacks that also work: `RadioParadise`
(`http://stream.radioparadise.com/mp3-128`) and SomaFM
(`http://ice1.somafm.com/groovesalad-128-mp3`).

## Stations known NOT to work

| Station | URL | Why |
|---|---|---|
| CNR 中国之声 | `http://ngcdn001.cnr.cn/live/zgzs/index.m3u8` | HLS |
| CNR 经济之声 | `http://ngcdn002.cnr.cn/live/jjzs/index.m3u8` | HLS |
| CNR 音乐之声 | `http://ngcdn003.cnr.cn/live/yyzs/index.m3u8` | 403 |

The CNR national channels only publish HLS, so there is no direct MP3 endpoint
for them. Use a provincial/city station instead.

## Notes

- These streams carry no ICY metadata, so the device shows the station name but
  no "now playing" title. That is normal, not a fault.
- `underruns` climbs during the first seconds of playback while the 64 KB input
  buffer fills. A steady count afterwards is fine; a count that keeps climbing
  means the Wi-Fi cannot keep up.
- `lhttp.qingting.fm` is HTTP only. There is no HTTPS endpoint, so no TLS
  handshake is needed and no extra heap is consumed.

## Why the Qingting stations stutter

Measured over several minutes per station, the Qingting FM endpoints deliver
about **9600 B/s** against the **8000 B/s** a 64 kbit/s stream needs to play.
That is enough on average, but delivery dips below 8000 B/s for **18-22% of
seconds**, and the dips last long enough to drain the input buffer.

The chain is:

```
delivery dips below 8000 B/s
  -> the 64 KB input buffer drains (it covers 8.2 s of outage at 64 kbit/s)
  -> the audio task finds an empty buffer and polls the socket every 5 ms
     (src/system/AudioOutEsp32.cpp, the `input.size() == consumed` branch)
  -> that polling contends with the render loop for the network stack and PSRAM
  -> fps falls from 42 to about 30
  -> the matrix visibly stutters
```

The fps drop is reproducible on any stream once the buffer empties, so it is a
consequence of the source, not of the device:

| Stream | fps with buffer > 16 KB | fps with buffer <= 16 KB |
|---|---|---|
| SomaFM (delivers 15308 B/s) | 42.0 | 31.1 |
| 南通交通 (delivers 9636 B/s) | 41.5 | 29.7 |

### Bitrate choice

A lower bitrate is better here, because the buffer covers more seconds of
outage. A 128 kbit/s stream needs 16000 B/s and so gets only 4.1 s of cover from
the same 64 KB, while a 64 kbit/s stream gets 8.2 s:

| Stream | needed | delivered | below need | buffer cover |
|---|---|---|---|---|
| 镇江交通 64k | 8000 B/s | 9611 B/s | 18% | **8.2 s** |
| 南通交通 64k | 8000 B/s | 9603 B/s | 22% | **8.2 s** |
| SomaFM Groove 128k | 16000 B/s | 17138 B/s | 50% | 4.1 s |
| RadioParadise 128k | 16000 B/s | 16833 B/s | 75% | 4.1 s |

### Brownout

A `resetReason` of `brownout` was observed while the radio played at brightness
200. The panel is the largest current draw and the supply has little headroom,
so playback plus a bright panel can reset the device. Keeping the brightness
well below its maximum avoids it.

### What cannot be fixed on the device

The source under-delivers. The buffer buys time but cannot create data. A
station that streams evenly, or a local relay, is the only real fix.

## Tools in this folder

| Script | Purpose |
|---|---|
| `radio_probe.py` | probe a candidate list, verdict per URL |
| `radio_probe_cn.py` | same, wider Chinese list |
| `radio_verify.py` | write a list and play every entry |
| `radio_set_cn.py` | write the verified Chinese list |
| `radio_play_check.py` | play one station, print counters |
| `radio_check_names.py` | report station names with odd characters |
| `radio_stutter.py` | sample counters to characterise stutter |
| `radio_netrate.py` | measure delivered bytes/s and gaps |
| `radio_bitrate.py` | compare bitrate endpoints of one station |
| `radio_ratewatch.py` | per-second delivery rate |
| `radio_connwatch.py` | detect server stalls and closes |
| `radio_fps.py` | sample fps next to the audio counters |
| `radio_analyse.py` | the arithmetic behind the buffer and DMA sizes |
| `radio_streamrate.py` | decode the stream, check audio vs wall time |
| `radio_delivery.py` | long-window delivered rate and deficit |
| `radio_rank.py` | rank stations by delivery steadiness |
| `radio_serial.py` | measure one station with no competing traffic |
| `radio_device_rank.py` | play each station, count underruns and low-fps seconds |
| `radio_report.py` | print the audio settings and buffer parameters in force |
| `radio_meta_test.py` | compare fps with radioMeta on and off |
| `radio_reset.py` | dump device facts including resetReason |
| `radio_brownout.py` | watch for brownout resets while playing |
| `radio_compare.py` | Chinese vs international stream stability |
| `radio_correlate.py` | prove the fps drop tracks the buffer level |
| `radio_best.py` | find the stream with the best rate/cover trade-off |
| `radio_tune.py` | apply the stutter-mitigation settings |
| `radio_apply.py` | final settings, with the reasoning printed |
