#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段四:批量获取每个条目的源站分类(MediaWiki 分类),作为归档依据。

输入:data/targets.jsonl
产出:data/categories.jsonl  每行 {"pageid":int, "title":str, "categories":[str]}

为什么用源站分类:分类是站点编者定义的归属,而不是我们猜测的。
prop=categories 支持一次查询多个标题,50 个/请求,成本远低于逐页抓取。

用法:
    python 04_fetch_categories.py            # 全量(可重复执行以续跑)
    python 04_fetch_categories.py --limit 200
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

from scrapling.fetchers import Fetcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://wiki.biligame.com/ys/api.php"
TARGETS = os.path.join(ROOT, "data", "targets.jsonl")
OUT = os.path.join(ROOT, "data", "categories.jsonl")

BATCH = 50          # MediaWiki 多标题查询上限
DELAY = 1.5         # 与阶段二抓取并行运行,放慢节奏,避免叠加触发 WAF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(TARGETS, encoding="utf-8")]
    done = {}
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                done[r["pageid"]] = r

    todo = [r for r in rows if r["pageid"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[续跑] 已有 {len(done)} 条,本轮待取 {len(todo)} 条")

    out = open(OUT, "a", encoding="utf-8")
    got = 0
    try:
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            titles = "|".join(c["title"] for c in chunk)
            cont = None
            cats = {}
            while True:
                q = (f"{API}?action=query&prop=categories&cllimit=max"
                     f"&titles={quote(titles)}&format=json")
                if cont:
                    q += f"&clcontinue={quote(cont)}"
                r = Fetcher.get(q, stealthy_headers=True, timeout=45)
                raw = r.body if isinstance(r.body, str) else r.body.decode("utf-8", "ignore")
                if r.status != 200 or not raw.lstrip().startswith("{"):
                    print(f"  [!] 非预期响应 status={r.status}", file=sys.stderr)
                    break
                d = json.loads(raw)
                for p in d.get("query", {}).get("pages", {}).values():
                    bucket = cats.setdefault(p.get("pageid"), [])
                    for c in p.get("categories", []):
                        t = c["title"]
                        if t.startswith("分类:"):
                            t = t[3:]
                        if t not in bucket:
                            bucket.append(t)
                cont = d.get("continue", {}).get("clcontinue")
                if not cont:
                    break
                time.sleep(DELAY)

            for c in chunk:
                rec = {
                    "pageid": c["pageid"], "title": c["title"],
                    "categories": cats.get(c["pageid"], []),
                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                got += 1
            out.flush()
            print(f"  已取 {got}/{len(todo)} …")
            time.sleep(DELAY)
    finally:
        out.close()
    print(f"[完成] 新增 {got} 条 -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
