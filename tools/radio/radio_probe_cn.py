"""Probe a wide set of Chinese radio stream URLs from public station directories.

Sources are the well known community station lists (radio-browser style mirrors
and the legacy Icecast endpoints Chinese broadcasters used before HLS). Only
streams that answer with audio/mpeg are kept.
"""
import concurrent.futures
import socket
import sys

TIMEOUT = 8

CANDIDATES = [
    # --- Qingting FM ids that already answered with audio/mpeg, named by the
    #     community station lists.
    ("北京交通广播", "http://lhttp.qingting.fm/live/1291/64k.mp3"),
    ("上海动感101", "http://lhttp.qingting.fm/live/273/64k.mp3"),
    ("江苏新闻广播", "http://lhttp.qingting.fm/live/4930/64k.mp3"),
    ("深圳飞扬971", "http://lhttp.qingting.fm/live/1270/64k.mp3"),
    # --- The same ids on the alternate qingting host, in case the CDN differs.
    ("上海动感101(alt)", "http://ls.qingting.fm/live/273/64k.mp3"),
    ("北京交通广播(alt)", "http://ls.qingting.fm/live/1291/64k.mp3"),
    # --- cnradio / cnr legacy mirrors
    ("CNR中国之声(mp3)", "http://ngcdn001.cnr.cn/live/zgzs/mp3"),
    ("CNR经济之声(mp3)", "http://ngcdn002.cnr.cn/live/jjzs/mp3"),
    # --- HLS variants of the public broadcasters, kept to show they still fail.
    ("CNR中国之声(hls)", "http://ngcdn001.cnr.cn/live/zgzs/index.m3u8"),
    # --- Other Chinese Icecast streams seen in station lists.
    ("佛山电台", "http://lhttp.qingting.fm/live/1260/64k.mp3"),
    ("无锡交通台", "http://lhttp.qingting.fm/live/1152/64k.mp3"),
    ("苏州新闻广播", "http://lhttp.qingting.fm/live/1153/64k.mp3"),
    ("常州交通台", "http://lhttp.qingting.fm/live/1154/64k.mp3"),
    ("南通交通台", "http://lhttp.qingting.fm/live/1155/64k.mp3"),
    ("扬州新闻台", "http://lhttp.qingting.fm/live/1156/64k.mp3"),
    ("徐州交通台", "http://lhttp.qingting.fm/live/1157/64k.mp3"),
    ("镇江交通台", "http://lhttp.qingting.fm/live/1158/64k.mp3"),
    ("泰州交通台", "http://lhttp.qingting.fm/live/1160/64k.mp3"),
    ("盐城交通台", "http://lhttp.qingting.fm/live/1262/64k.mp3"),
    ("淮安交通台", "http://lhttp.qingting.fm/live/1263/64k.mp3"),
    ("连云港交通台", "http://lhttp.qingting.fm/live/1271/64k.mp3"),
    ("宿迁交通台", "http://lhttp.qingting.fm/live/1272/64k.mp3"),
    ("江阴电台", "http://lhttp.qingting.fm/live/1273/64k.mp3"),
    ("宜兴电台", "http://lhttp.qingting.fm/live/1274/64k.mp3"),
    ("昆山电台", "http://lhttp.qingting.fm/live/1275/64k.mp3"),
    ("张家港电台", "http://lhttp.qingting.fm/live/1295/64k.mp3"),
    ("常熟电台", "http://lhttp.qingting.fm/live/1301/64k.mp3"),
    ("太仓电台", "http://lhttp.qingting.fm/live/1303/64k.mp3"),
    ("吴江电台", "http://lhttp.qingting.fm/live/4900/64k.mp3"),
    ("溧阳电台", "http://lhttp.qingting.fm/live/4901/64k.mp3"),
    ("金坛电台", "http://lhttp.qingting.fm/live/4904/64k.mp3"),
    ("丹阳电台", "http://lhttp.qingting.fm/live/4905/64k.mp3"),
    ("句容电台", "http://lhttp.qingting.fm/live/4932/64k.mp3"),
    ("扬中电台", "http://lhttp.qingting.fm/live/4970/64k.mp3"),
    # --- id 266/267/269/270/274/275/276/332/333/336/339/345/468..471
    ("频道266", "http://lhttp.qingting.fm/live/266/64k.mp3"),
    ("频道267", "http://lhttp.qingting.fm/live/267/64k.mp3"),
    ("频道269", "http://lhttp.qingting.fm/live/269/64k.mp3"),
    ("频道270", "http://lhttp.qingting.fm/live/270/64k.mp3"),
    ("频道274", "http://lhttp.qingting.fm/live/274/64k.mp3"),
    ("频道275", "http://lhttp.qingting.fm/live/275/64k.mp3"),
    ("频道276", "http://lhttp.qingting.fm/live/276/64k.mp3"),
    ("频道332", "http://lhttp.qingting.fm/live/332/64k.mp3"),
    ("频道333", "http://lhttp.qingting.fm/live/333/64k.mp3"),
    ("频道336", "http://lhttp.qingting.fm/live/336/64k.mp3"),
    ("频道339", "http://lhttp.qingting.fm/live/339/64k.mp3"),
    ("频道345", "http://lhttp.qingting.fm/live/345/64k.mp3"),
    ("频道468", "http://lhttp.qingting.fm/live/468/64k.mp3"),
    ("频道469", "http://lhttp.qingting.fm/live/469/64k.mp3"),
    ("频道470", "http://lhttp.qingting.fm/live/470/64k.mp3"),
    ("频道471", "http://lhttp.qingting.fm/live/471/64k.mp3"),
]


def split(url):
    tls = url.startswith("https://")
    rest = url.split("://", 1)[1]
    slash = rest.find("/")
    hostport, path = (rest, "/") if slash < 0 else (rest[:slash], rest[slash:])
    if ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        port = int(port_s)
    else:
        host, port = hostport, 443 if tls else 80
    return host, port, path, tls


def probe(item):
    name, url = item
    host, port, path, _ = split(url)
    try:
        sock = socket.create_connection((host, port), TIMEOUT)
    except OSError as exc:
        return name, url, "UNREACHABLE", str(exc)[:40]
    try:
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: AWTRIX-NG\r\n"
               "Icy-MetaData: 1\r\nConnection: close\r\n\r\n")
        sock.sendall(req.encode())
        sock.settimeout(TIMEOUT)
        chunk = sock.recv(2048)
    except OSError as exc:
        return name, url, "ERROR", str(exc)[:40]
    finally:
        sock.close()
    head = chunk.split(b"\r\n\r\n", 1)[0].decode("latin-1", "replace")
    lines = head.splitlines()
    status = lines[0] if lines else ""
    if "200" not in status:
        return name, url, "HTTP", status[:40]
    low = head.lower()
    if "audio/mpeg" in low or "icy-" in low:
        return name, url, "OK-MP3", "audio/mpeg"
    if "mpegurl" in low:
        return name, url, "HLS", "HLS playlist"
    return name, url, "OTHER", low.split("content-type:")[-1].strip()[:40]


def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for r in pool.map(probe, CANDIDATES):
            results.append(r)
    ok = [r for r in results if r[2] == "OK-MP3"]
    print(f"# {len(ok)} / {len(results)} usable\n")
    for name, url, verdict, detail in results:
        mark = "OK " if verdict == "OK-MP3" else "   "
        print(f"{mark}{verdict:<12} {name:<20} {url}")
    print("\n== usable JSON ==")
    for name, url, _, _ in ok:
        print(f'{{"name":"{name}","url":"{url}"}},')


if __name__ == "__main__":
    sys.exit(main())
