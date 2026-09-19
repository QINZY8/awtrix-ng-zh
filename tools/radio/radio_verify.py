"""Set the station list on a device and verify each station actually plays.

Playback is judged by the device's own counters: a working stream makes
bufferBytes climb and eventually fills in a title, while a dead one leaves
bufferBytes pinned and the title empty.
"""
import json
import sys
import time
import urllib.error
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.5.16"
BASE = f"http://{HOST}"

STATIONS = [
    {"name": "北京交通", "url": "http://lhttp.qingting.fm/live/1291/64k.mp3"},
    {"name": "上海动感101", "url": "http://lhttp.qingting.fm/live/273/64k.mp3"},
    {"name": "江苏新闻", "url": "http://lhttp.qingting.fm/live/4930/64k.mp3"},
    {"name": "深圳飞扬971", "url": "http://lhttp.qingting.fm/live/1270/64k.mp3"},
    {"name": "佛山电台", "url": "http://lhttp.qingting.fm/live/1260/64k.mp3"},
    {"name": "无锡交通", "url": "http://lhttp.qingting.fm/live/1152/64k.mp3"},
    {"name": "苏州新闻", "url": "http://lhttp.qingting.fm/live/1153/64k.mp3"},
    {"name": "常州交通", "url": "http://lhttp.qingting.fm/live/1154/64k.mp3"},
    {"name": "南通交通", "url": "http://lhttp.qingting.fm/live/1155/64k.mp3"},
    {"name": "扬州新闻", "url": "http://lhttp.qingting.fm/live/1156/64k.mp3"},
    {"name": "徐州交通", "url": "http://lhttp.qingting.fm/live/1157/64k.mp3"},
    {"name": "镇江交通", "url": "http://lhttp.qingting.fm/live/1158/64k.mp3"},
    {"name": "泰州交通", "url": "http://lhttp.qingting.fm/live/1160/64k.mp3"},
    {"name": "盐城交通", "url": "http://lhttp.qingting.fm/live/1262/64k.mp3"},
    {"name": "淮安交通", "url": "http://lhttp.qingting.fm/live/1263/64k.mp3"},
    {"name": "连云港交通", "url": "http://lhttp.qingting.fm/live/1271/64k.mp3"},
    {"name": "宿迁交通", "url": "http://lhttp.qingting.fm/live/1272/64k.mp3"},
    {"name": "江阴电台", "url": "http://lhttp.qingting.fm/live/1273/64k.mp3"},
    {"name": "宜兴电台", "url": "http://lhttp.qingting.fm/live/1274/64k.mp3"},
    {"name": "昆山电台", "url": "http://lhttp.qingting.fm/live/1275/64k.mp3"},
    {"name": "张家港电台", "url": "http://lhttp.qingting.fm/live/1295/64k.mp3"},
    {"name": "常熟电台", "url": "http://lhttp.qingting.fm/live/1301/64k.mp3"},
    {"name": "太仓电台", "url": "http://lhttp.qingting.fm/live/1303/64k.mp3"},
    {"name": "吴江电台", "url": "http://lhttp.qingting.fm/live/4900/64k.mp3"},
    {"name": "溧阳电台", "url": "http://lhttp.qingting.fm/live/4901/64k.mp3"},
    {"name": "金坛电台", "url": "http://lhttp.qingting.fm/live/4904/64k.mp3"},
    {"name": "丹阳电台", "url": "http://lhttp.qingting.fm/live/4905/64k.mp3"},
    {"name": "句容电台", "url": "http://lhttp.qingting.fm/live/4932/64k.mp3"},
    {"name": "扬中电台", "url": "http://lhttp.qingting.fm/live/4970/64k.mp3"},
    {"name": "RadioParadise", "url": "http://stream.radioparadise.com/mp3-128"},
    {"name": "SomaFM", "url": "http://ice1.somafm.com/groovesalad-128-mp3"},
]


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def audio():
    _, body = call("GET", "/api/v1/audio")
    return json.loads(body)


def main():
    print(call("PUT", "/api/v1/audio/stations", {"stations": STATIONS}))
    s = audio()
    print(f"stations stored: {len(s['stations'])}")

    for st in STATIONS:
        name = st["name"]
        call("POST", "/api/v1/audio/play", {"station": name})
        peak = 0
        title = ""
        err = ""
        for _ in range(5):
            time.sleep(2)
            r = audio()["radio"]
            peak = max(peak, r["bufferBytes"])
            title = r["title"] or title
            err = r["error"] or err
        verdict = "OK " if peak > 20000 or title else "?? "
        print(f"{verdict}{name:<14} peakBuf={peak:>6}  title={title[:40]!r} err={err[:40]!r}")
        call("POST", "/api/v1/audio/stop")
        time.sleep(1)


if __name__ == "__main__":
    main()
