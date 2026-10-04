#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段一:枚举 BWIKI 原神站(wiki.biligame.com/ys)主命名空间(ns=0)全部条目。

产出:data/pages.jsonl,每行一个 JSON:{"pageid": int, "title": str}
依据:robots.txt 允许 /ys/ 下的条目页;仅取主命名空间,避开被 Disallow 的
      模板/文件/特殊/User/MediaWiki 等命名空间。
"""
import json
import os
import sys
import time

from scrapling.fetchers import Fetcher

API = "https://wiki.biligame.com/ys/api.php"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "pages.jsonl")
DELAY = 0.6  # 请求间隔(秒),对反爬与站点负载都友好


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    seen, cont = [], None
    while True:
        q = (f"{API}?action=query&list=allpages&apnamespace=0"
             f"&aplimit=500&apfilterredir=nonredirects&format=json")
        if cont:
            q += f"&apcontinue={cont}"
        r = Fetcher.get(q, stealthy_headers=True, timeout=30)
        raw = r.body if isinstance(r.body, str) else r.body.decode("utf-8", "ignore")
        if r.status != 200 or not raw.lstrip().startswith("{"):
            print(f"[!] 非预期响应 status={r.status},前 120 字: {raw[:120]!r}", file=sys.stderr)
            sys.exit(1)
        d = json.loads(raw)
        batch = d.get("query", {}).get("allpages", [])
        for p in batch:
            seen.append({"pageid": p["pageid"], "title": p["title"]})
        print(f"  已枚举 {len(seen)} 条 …", file=sys.stderr)
        cont = d.get("continue", {}).get("apcontinue")
        if not cont:
            break
        time.sleep(DELAY)

    with open(OUT, "w", encoding="utf-8") as f:
        for p in seen:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"完成:共 {len(seen)} 条 -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
