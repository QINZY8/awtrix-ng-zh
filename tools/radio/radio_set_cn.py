"""Write the verified Chinese radio stations to an AWTRIX device.

Only the stations that were confirmed to buffer and play are listed. Names are
kept short because the AWTRIX station name field is capped at 24 characters and
the matrix display is narrow.
"""
import json
import sys
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
]


def main():
    payload = json.dumps({"stations": STATIONS}).encode()
    req = urllib.request.Request(BASE + "/api/v1/audio/stations", data=payload,
                                method="PUT")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            print(f"PUT stations -> {r.status} {r.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"PUT stations -> {e.code} {e.read().decode()}")
        return 1

    with urllib.request.urlopen(BASE + "/api/v1/audio", timeout=25) as r:
        state = json.loads(r.read().decode())
    print(f"stored: {len(state['stations'])} stations")
    for i, st in enumerate(state["stations"]):
        print(f"  {i:>2}  {st['name']:<14} {st['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
