#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段二:批量抓取正文(渲染 HTML),带限速与断点续跑。

输入:data/pages.jsonl        (阶段一产出的 ns=0 全量清单)
产出:data/targets.jsonl      (过滤后的抓取目标)
      cache/raw/<pageid>.html (原始渲染 HTML,已被 .gitignore 排除)
      data/fetch_log.jsonl    (逐页抓取记录:pageid/title/status/bytes/时间)

过滤规则:排除 Data:Map* 点位数据(实测其内容为「图片引用 + 数十字标签」,
          属地图标记而非 wiki 文本,与本仓库「只收录 wikitxt」的定位不符)。

用法:
    python 02_fetch_content.py                # 全量抓取(可重复执行以续跑)
    python 02_fetch_content.py --limit 10     # 先跑 10 条做试点
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from scrapling.fetchers import Fetcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://wiki.biligame.com/ys/api.php"
PAGES = os.path.join(ROOT, "data", "pages.jsonl")
TARGETS = os.path.join(ROOT, "data", "targets.jsonl")
RAW_DIR = os.path.join(ROOT, "cache", "raw")
LOG = os.path.join(ROOT, "data", "fetch_log.jsonl")

DELAY = 0.8          # 请求间隔(秒):实测 0.6s 可稳定穿过 EdgeOne,WAF 留足余量
EXCLUDE_PREFIX = "Data:Map"   # 地图点位数据,不属于文本内容


def build_targets():
    rows = [json.loads(l) for l in open(PAGES, encoding="utf-8")]
    keep = [r for r in rows if not r["title"].startswith(EXCLUDE_PREFIX)]
    with open(TARGETS, "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[目标] 全量 {len(rows)} 条,排除 '{EXCLUDE_PREFIX}*' 后保留 {len(keep)} 条")
    return keep


def load_done():
    """已成功的 pageid 集合,用于断点续跑。"""
    done = set()
    if os.path.exists(LOG):
        for ln in open(LOG, encoding="utf-8"):
            try:
                r = json.loads(ln)
                if r.get("status") == 200 and r.get("has_content"):
                    done.add(r["pageid"])
            except Exception:
                pass
    return done


def fetch_one(pageid: int):
    """用 pageid 取渲染 HTML,避免标题编码问题。"""
    q = (f"{API}?action=parse&pageid={pageid}&prop=text"
         f"&disabletoc=1&disableeditsection=1&disablelimitreport=1&format=json")
    r = Fetcher.get(q, stealthy_headers=True, timeout=40)
    raw = r.body if isinstance(r.body, str) else r.body.decode("utf-8", "ignore")
    if r.status != 200 or not raw.lstrip().startswith("{"):
        return r.status, None
    d = json.loads(raw)
    if "error" in d:
        return f"api:{d['error'].get('code')}", None
    return 200, d["parse"]["text"]["*"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="仅抓前 N 条(试点用)")
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)
    targets = build_targets()
    done = load_done()
    todo = [t for t in targets if t["pageid"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[续跑] 已完成 {len(done)} 条,本轮待抓 {len(todo)} 条")

    logf = open(LOG, "a", encoding="utf-8")
    ok = fail = 0
    try:
        for i, t in enumerate(todo, 1):
            pid, title = t["pageid"], t["title"]
            try:
                status, html = fetch_one(pid)
            except Exception as e:
                status, html = f"exc:{type(e).__name__}", None
            has = bool(html and len(html) > 200)
            if status == 200 and has:
                with open(os.path.join(RAW_DIR, f"{pid}.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                ok += 1
            else:
                fail += 1
            rec = {
                "pageid": pid, "title": title, "status": status,
                "bytes": len(html) if html else 0, "has_content": has,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            logf.flush()
            if i % 10 == 0 or status != 200:
                print(f"  [{i}/{len(todo)}] ok={ok} fail={fail} 最近: {title[:20]} -> {status}")
            time.sleep(DELAY)
    finally:
        logf.close()
    print(f"[完成] 成功 {ok} 条,失败 {fail} 条。原始 HTML -> cache/raw/")


if __name__ == "__main__":
    main()
