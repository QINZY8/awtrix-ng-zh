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
