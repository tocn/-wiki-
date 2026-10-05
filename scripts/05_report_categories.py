#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分类诊断工具(只读,不改动任何文件)。

用途:查看当前分类分布、映射覆盖率与判定来源,验证分类法是否完备。

阶段三已直接写入分类目录,因此本工具不再承担「重排」职责 ——
早期版本在此处做文件移动与陈旧清理,因同时存在旧分类目录与扁平中间态而误删文件。
删除路径已彻底移除:本工具只读不写。

用法:
    python 05_report_categories.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from taxonomy import coverage  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "data", "index.jsonl")
CATS = os.path.join(ROOT, "data", "categories.jsonl")
MD_DIR = os.path.join(ROOT, "data", "md")


def main():
    idx = [json.loads(l) for l in open(INDEX, encoding="utf-8") if l.strip()]
    cats, title2cat = {}, {}
    if os.path.exists(CATS):
        for l in open(CATS, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                cats[r["pageid"]] = r["categories"]
                title2cat[r["title"]] = r["categories"]

    st = coverage(idx, cats, title2cat)
    have = sum(1 for r in idx if cats.get(r["pageid"]))
    print(f"条目总数: {len(idx)}   已取到源站分类: {have}")
    print(f"内容分类数: {st['distinct']}   命中映射: {st['mapped']}")
    print(f"分类使用量覆盖率: {st['covered_usage']}/{st['total_usage']} = {st['coverage_pct']:.1f}%")

    print("\n=== 未映射的分类(按使用量) ===")
    if st["unmapped"]:
        for c, n in sorted(st["unmapped"].items(), key=lambda x: -x[1])[:40]:
            print(f"  {n:>5}  {c}")
    else:
        print("  (无)")

    print("\n=== 各大类条目数 ===")
    for k, v in st["buckets"].most_common():
        print(f"  {v:>6}  {k}")

    print("\n=== 判定来源 ===")
    label = {"wiki": "源站分类(权威)", "parent": "继承父页面分类",
             "title": "标题关键词兜底", "none": "仍无法判定 -> 未分类"}
    for k, v in st["sources"].most_common():
        print(f"  {v:>6}  {label.get(k, k)}")

    # 一致性校验:索引 vs 磁盘
    missing = [r for r in idx if not os.path.exists(os.path.join(ROOT, r["file"]))]
    disk = set()
    for dp, _, fs in os.walk(MD_DIR):
        for f in fs:
            if f.endswith(".md"):
                disk.add(os.path.abspath(os.path.join(dp, f)))
    expected = {os.path.abspath(os.path.join(ROOT, r["file"])) for r in idx}
    orphan = disk - expected
    print("\n=== 一致性校验 ===")
    print(f"  磁盘 md 文件数: {len(disk)}")
    print(f"  索引指向不存在的文件: {len(missing)}")
    print(f"  磁盘上不在索引中的文件: {len(orphan)}")
    if missing or orphan:
        print("  [!] 存在不一致,请核对后再提交")


if __name__ == "__main__":
    main()
