#!/usr/bin/env python3
"""下载 Readable 游戏内书籍正文（DimbreathBot/AnimeGameData）。

背景：TextMap 不含书籍正文；书籍正文在仓库另行的 `Readable/<语言>/` 下。
本脚本按 `cache/readable.json`（GitHub tree 快照）所列清单，断点续传式补齐。

用法:
  python scripts/07_download_readable.py --langs CHS
  python scripts/07_download_readable.py --langs CHS,EN,DE,RU
  python scripts/07_download_readable.py --langs EN --only Book1132,Book1131

要点:
  - CHS 目录文件名无后缀（Book1132.txt）；其它语言带后缀（Book1132_EN.txt）。
  - 用 urllib（Python 自带 TLS）。注意本机 curl 命中 schannel 撤销检查会间歇
    SSL connect error（exit 35）。
  - **并发务必低**（默认 1）：实测高并发/每文件新连接会触发 CDN 限流，速度反降
    到 ~5/分钟；单线程顺序请求反而快得多。
  - 仅本地留存，不入库（客户端 dump 属灰区）。
"""
import argparse
import json
import os
import ssl
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/main/Readable"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
OUTDIR = os.path.join(CACHE, "readable")
TREEFILE = os.path.join(CACHE, "readable.json")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=25, context=CTX) as r:
                return r.read()
        except Exception:
            time.sleep(0.2 * (i + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="CHS")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--tries", type=int, default=5)
    args = ap.parse_args()

    tree = json.load(open(TREEFILE, encoding="utf-8"))
    paths = {e["path"] for e in tree["tree"] if e.get("type") == "blob"}
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    for lang in [s.strip() for s in args.langs.split(",") if s.strip()]:
        want = sorted(p for p in paths if p.startswith(lang + "/") and p.endswith(".txt"))
        if only:
            want = [p for p in want if os.path.basename(p).split("_")[0] in only]
        dest = os.path.join(OUTDIR, lang)
        os.makedirs(dest, exist_ok=True)

        todo = [p for p in want
                if not (os.path.exists(os.path.join(dest, p.split("/", 1)[1]))
                        and os.path.getsize(os.path.join(dest, p.split("/", 1)[1])) > 0)]
        print(f"[{lang}] 清单 {len(want)}，待下 {len(todo)}，并发 {args.workers}", flush=True)

        ok = fail = 0
        t0 = time.time()
        if args.workers <= 1:
            for p in todo:
                name = p.split("/", 1)[1]
                data = fetch(f"{BASE}/{p}", args.tries)
                if data is None:
                    fail += 1
                    print(f"   ! FAIL {name}", flush=True)
                    continue
                with open(os.path.join(dest, name), "wb") as w:
                    w.write(data)
                ok += 1
                if ok % 100 == 0:
                    el = time.time() - t0
                    print(f"   … {ok}/{len(todo)}  ({el:.0f}s, {ok/max(el,1)*60:.0f}/min)", flush=True)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = {ex.submit(fetch, f"{BASE}/{p}", args.tries): p for p in todo}
                for fu in as_completed(futs):
                    p = futs[fu]
                    name = p.split("/", 1)[1]
                    data = fu.result()
                    if data is None:
                        fail += 1
                        print(f"   ! FAIL {name}", flush=True)
                        continue
                    with open(os.path.join(dest, name), "wb") as w:
                        w.write(data)
                    ok += 1
                    if ok % 100 == 0:
                        el = time.time() - t0
                        print(f"   … {ok}/{len(todo)}  ({el:.0f}s, {ok/max(el,1)*60:.0f}/min)", flush=True)

        have = len([f for f in os.listdir(dest) if f.endswith(".txt")])
        print(f"[{lang}] 完成: 新增 {ok}，失败 {fail}，现有 {have}/{len(want)}", flush=True)

    print("全部完成", flush=True)


if __name__ == "__main__":
    main()
