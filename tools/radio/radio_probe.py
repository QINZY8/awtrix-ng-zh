"""Probe candidate Chinese radio stream URLs and report which ones are usable.

A stream is usable when AWTRIX can decode it: the response must be an MP3 stream
(Content-Type audio/mpeg or an icy-* header), not an HLS playlist (.m3u8) and not
a plain HTML page.
"""
import concurrent.futures
import socket
import ssl
import sys

TIMEOUT = 8

CANDIDATES = [
    # --- CNR (央广) direct streams; the official ones are HLS, these are the
    #     legacy Icecast mirrors that some CDNs still serve as MP3.
    ("CNR中国之声", "http://ngcdn001.cnr.cn/live/zgzs/index.m3u8"),
    ("CNR经济之声", "http://ngcdn002.cnr.cn/live/jjzs/index.m3u8"),
    ("CNR音乐之声", "http://ngcdn003.cnr.cn/live/yyzs/index.m3u8"),
    # --- Qingting FM (蜻蜓FM) direct mp3 endpoints
    ("蜻蜓-中国之声", "http://lhttp.qingting.fm/live/386/64k.mp3"),
    ("蜻蜓-经济之声", "http://lhttp.qingting.fm/live/387/64k.mp3"),
    ("蜻蜓-音乐之声", "http://lhttp.qingting.fm/live/388/64k.mp3"),
    ("蜻蜓-北京交通", "http://lhttp.qingting.fm/live/1291/64k.mp3"),
    ("蜻蜓-上海动感101", "http://lhttp.qingting.fm/live/273/64k.mp3"),
    # --- Other Chinese Icecast/Shoutcast mirrors
    ("江苏新闻广播", "http://lhttp.qingting.fm/live/4930/64k.mp3"),
    ("浙江交通之声", "http://lhttp.qingting.fm/live/1151/64k.mp3"),
    ("广东音乐之声", "http://lhttp.qingting.fm/live/1264/64k.mp3"),
    ("深圳飞扬971", "http://lhttp.qingting.fm/live/1270/64k.mp3"),
    # --- International MP3 streams, known good, as a fallback
    ("RadioParadise", "http://stream.radioparadise.com/mp3-128"),
    ("SomaFM GrooveSalad", "http://ice1.somafm.com/groovesalad-128-mp3"),
    ("SomaFM Lush", "http://ice1.somafm.com/lush-128-mp3"),
]


def probe(name, url):
    """Return (name, url, verdict, detail)."""
    host, port, path, tls = _split(url)
    if host is None:
        return name, url, "BAD-URL", url
    try:
        sock = socket.create_connection((host, port), TIMEOUT)
    except OSError as exc:
        return name, url, "UNREACHABLE", str(exc)
    try:
        if tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sock = ctx.wrap_socket(sock, server_hostname=host)
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: AWTRIX-NG\r\n"
            "Icy-MetaData: 1\r\n"
            "Connection: close\r\n\r\n"
        )
        sock.sendall(req.encode())
        sock.settimeout(TIMEOUT)
        chunk = sock.recv(2048)
    except OSError as exc:
        return name, url, "ERROR", str(exc)
    finally:
        sock.close()

    head = chunk.split(b"\r\n\r\n", 1)[0].decode("latin-1", "replace")
    lines = [l.strip() for l in head.splitlines()]
    status = lines[0] if lines else ""
    ctype = ""
    icy = ""
    for line in lines:
        low = line.lower()
        if low.startswith("content-type:"):
            ctype = line.split(":", 1)[1].strip().lower()
        elif low.startswith("icy-name:") or low.startswith("icy-br:"):
            icy += line + " "
    if "200" not in status:
        return name, url, "HTTP", status
    if "audio/mpeg" in ctype or "audio/aac" in ctype or icy:
        return name, url, "OK-MP3", f"{ctype} {icy}".strip()
    if "mpegurl" in ctype:
        return name, url, "HLS", ctype
    return name, url, "OTHER", ctype or status


def _split(url):
    if not url.startswith(("http://", "https://")):
        return None, None, None, False
    tls = url.startswith("https://")
    rest = url.split("://", 1)[1]
    slash = rest.find("/")
    if slash < 0:
        hostport, path = rest, "/"
    else:
        hostport, path = rest[:slash], rest[slash:]
    if ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        port = int(port_s)
    else:
        host, port = hostport, 443 if tls else 80
    return host, port, path, tls


def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for r in pool.map(lambda a: probe(*a), CANDIDATES):
            results.append(r)
    order = {"OK-MP3": 0, "HLS": 1, "OTHER": 2, "HTTP": 3, "ERROR": 4,
             "UNREACHABLE": 5, "BAD-URL": 6}
    results.sort(key=lambda r: order.get(r[2], 9))
    print(f"{'verdict':<12} {'name':<22} detail")
    print("-" * 90)
    for name, url, verdict, detail in results:
        print(f"{verdict:<12} {name:<22} {detail[:60]}")
    print("\n== usable (OK-MP3) ==")
    for name, url, verdict, _ in results:
        if verdict == "OK-MP3":
            print(f'{{"name":"{name}","url":"{url}"}},')


if __name__ == "__main__":
    sys.exit(main())
