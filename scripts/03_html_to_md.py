#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段三:把原始渲染 HTML 清洗并转换为 Markdown。

输入:data/fetch_log.jsonl      (阶段二记录)
      cache/raw/<pageid>.html  (阶段二原始产物)
产出:data/md/<标题>.md         (最终交付物)
      data/index.jsonl         (pageid <-> 标题 <-> 文件 映射,供检索与核对)

用法:
    python 03_html_to_md.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import clean, safe_filename  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "cache", "raw")
MD_DIR = os.path.join(ROOT, "data", "md")
LOG = os.path.join(ROOT, "data", "fetch_log.jsonl")
INDEX = os.path.join(ROOT, "data", "index.jsonl")
SITE = "https://wiki.biligame.com/ys/"


def strip_rule_lines(text: str) -> str:
    """去掉清洗后残留的独立分隔线(markdownify 由 <hr> 生成)。"""
    lines = [l for l in text.splitlines()]
    while lines and lines[0].strip() in ("", "---", "***", "___"):
        lines.pop(0)
    while lines and lines[-1].strip() in ("", "---", "***", "___"):
        lines.pop()
    return "\n".join(lines).strip()


def main():
    os.makedirs(MD_DIR, exist_ok=True)
    recs = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]
    ok = skip = fail = 0
    used = {}
    index = []

    for r in recs:
        if not r.get("has_content"):
            continue
        pid, title = r["pageid"], r["title"]
        src = os.path.join(RAW_DIR, f"{pid}.html")
        if not os.path.exists(src):
            fail += 1
            print(f"  [!] 缺少原始文件: {pid} {title}", file=sys.stderr)
            continue

        body = strip_rule_lines(clean(open(src, encoding="utf-8").read()))
        if len(body) < 30:
            skip += 1
            continue

        # 同名标题去重:追加 pageid
        base = safe_filename(title)
        fname = f"{base}.md"
        if fname in used:
            fname = f"{base}__{pid}.md"
        used[fname] = pid

        fm = (f"---\n"
              f"title: {title}\n"
              f"pageid: {pid}\n"
              f"source: {SITE}{title}\n"
              f"fetched_at: {r.get('fetched_at', '')}\n"
              f"---\n\n")
        with open(os.path.join(MD_DIR, fname), "w", encoding="utf-8") as f:
            f.write(fm + body + "\n")

        index.append({"pageid": pid, "title": title, "file": f"data/md/{fname}",
                      "chars": len(body)})
        ok += 1

    with open(INDEX, "w", encoding="utf-8") as f:
        for r in index:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[完成] 转换 {ok} 篇,过短跳过 {skip} 篇,缺原始文件 {fail} 篇")
    print(f"       产物目录: data/md/   索引: data/index.jsonl")


if __name__ == "__main__":
    main()
