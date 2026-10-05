#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
阶段三:把原始渲染 HTML 清洗并转换为 Markdown,并直接写入分类目录。

输入:data/fetch_log.jsonl      (阶段二记录)
      cache/raw/<pageid>.html  (阶段二原始产物)
      data/categories.jsonl    (阶段四:源站分类;不存在时全部归入「未分类」)
产出:data/md/<大类>/<标题>.md  (最终交付物)
      data/index.jsonl         (pageid <-> 标题 <-> 文件 <-> 分类)

设计说明:
- **直接写入分类目录**,不再产出「扁平中间态」。早期版本先写扁平、再由阶段五移动,
  结果同一篇文章可能同时存在于旧分类目录与扁平位置,移动时顾此失彼、遗留重复副本,
  清理又误删。一个文件只应有一个家。
- **并行处理**:逐篇解析大体积 HTML 是瓶颈,用进程池按 CPU 数并行。
- **不删除任何文件**:落单的文件被移入 cache/orphan/ 并报告。
  宁可留下可追溯的残件,也不做不可逆删除。

用法:
    python 03_html_to_md.py
"""
import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clean import clean, safe_filename, is_junk_title  # noqa: E402
from taxonomy import resolve  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "cache", "raw")
MD_DIR = os.path.join(ROOT, "data", "md")
ORPHAN_DIR = os.path.join(ROOT, "cache", "orphan")
LOG = os.path.join(ROOT, "data", "fetch_log.jsonl")
INDEX = os.path.join(ROOT, "data", "index.jsonl")
CATS = os.path.join(ROOT, "data", "categories.jsonl")
SITE = "https://wiki.biligame.com/ys/"

FM = ("---\ntitle: {title}\npageid: {pageid}\nsource: {site}{title}\n"
      "fetched_at: {at}\n---\n\n")


def strip_rule_lines(text):
    """去掉清洗后残留的独立分隔线(markdownify 由 <hr> 生成)。"""
    lines = text.splitlines()
    while lines and lines[0].strip() in ("", "---", "***", "___"):
        lines.pop(0)
    while lines and lines[-1].strip() in ("", "---", "***", "___"):
        lines.pop()
    return "\n".join(lines).strip()


def _worker(job):
    """在子进程中执行清洗(CPU 密集),只回传文本,不碰文件系统。"""
    pid, title, at = job
    src = os.path.join(RAW_DIR, f"{pid}.html")
    try:
        body = strip_rule_lines(clean(open(src, encoding="utf-8").read()))
    except Exception as e:
        return pid, title, at, None, f"{type(e).__name__}: {e}"
    return pid, title, at, body, None


def load_categories():
    cats = {}
    if os.path.exists(CATS):
        for l in open(CATS, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                cats[r["pageid"]] = r["categories"]
    return cats


def write_jsonl_atomic(path, rows, retries=6):
    """
    原子写入 JSONL:先写临时文件再 os.replace。
    并对瞬时文件锁做重试 —— 上一轮被中断的进程可能短暂持有句柄,
    若无重试,整轮数分钟的转换成果会因一次 PermissionError 白费。
    """
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for i in range(retries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == retries - 1:
                raise
            time.sleep(0.5 * (i + 1))


def main():
    os.makedirs(MD_DIR, exist_ok=True)
    cats = load_categories()
    recs = [json.loads(l) for l in open(LOG, encoding="utf-8") if l.strip()]

    jobs, skipped = [], 0
    for r in recs:
        if not r.get("has_content") or is_junk_title(r["title"]):
            skipped += 1
            continue
        jobs.append((r["pageid"], r["title"], r.get("fetched_at", "")))

    workers = min(max((os.cpu_count() or 4) - 1, 2), 12)
    print(f"[转换] 待处理 {len(jobs)} 篇,并行度 {workers}")

    index, ok, failed, too_short = [], 0, 0, 0
    used = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for pid, title, at, body, err in ex.map(_worker, jobs, chunksize=8):
            if err:
                failed += 1
                print(f"  [!] {title}: {err}", file=sys.stderr)
                continue
            if not body or len(body) < 30:
                too_short += 1
                continue

            base = safe_filename(title)
            fname = f"{base}.md"
            if fname in used:
                fname = f"{base}__{pid}.md"
            used[fname] = pid

            folder, source = resolve(cats.get(pid, []), title)
            os.makedirs(os.path.join(MD_DIR, folder), exist_ok=True)
            with open(os.path.join(MD_DIR, folder, fname), "w", encoding="utf-8") as f:
                f.write(FM.format(title=title, pageid=pid, site=SITE, at=at) + body + "\n")
            index.append({"pageid": pid, "title": title, "category": folder,
                          "category_source": source,
                          "file": f"data/md/{folder}/{fname}", "chars": len(body)})
            ok += 1

    write_jsonl_atomic(INDEX, index)

    # 落单文件:不在索引中 -> 移入 cache/orphan/(移动而非删除,可追溯)
    expected = {os.path.abspath(os.path.join(ROOT, r["file"])) for r in index}
    orphans = []
    for dirpath, _, files in os.walk(MD_DIR):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.abspath(os.path.join(dirpath, fn))
            if p not in expected:
                orphans.append(p)
    for p in orphans:
        rel = os.path.relpath(p, MD_DIR).replace(os.sep, "__")
        os.makedirs(ORPHAN_DIR, exist_ok=True)
        shutil.move(p, os.path.join(ORPHAN_DIR, rel))

    print(f"[完成] 转换 {ok} 篇,过短跳过 {too_short} 篇,处理失败 {failed} 篇,"
          f"非文本跳过 {skipped} 篇")
    if orphans:
        print(f"       落单 {len(orphans)} 篇已移至 cache/orphan/(未删除),可人工核对")
    print(f"       产物目录: data/md/<大类>/   索引: data/index.jsonl")


if __name__ == "__main__":
    main()
