# -*- coding: utf-8 -*-
"""
TextMap 多语言对照查询工具（世界观名词词典用）

用法：
  PY="C:/Users/admin/.workbuddy/binaries/python/versions/3.13.12/python.exe"
  "$PY" scripts/06_textmap_lookup.py --langs CHS,EN,DE --grep 三宝磨 亚原子质能衍构核心
  "$PY" scripts/06_textmap_lookup.py --langs CHS,EN,DE            # 精确反查内置词

说明：
  TextMap 是【句子级】资源，词条名多嵌在句子里、不单独成条。
  故「找某名词的外文」通常要用【子串检索】(--grep)，而非精确键查询。
数据来源：DimbreathBot/AnimeGameData @ main（客户端解包，仅本地比对用，不入库）
"""
import argparse
import json
import os

BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "textmap"
)
FILES = {
    "CHS": ["TextMapCHS.json"],
    "EN": ["TextMapEN.json"],
    "DE": ["TextMapDE.json"],
    "RU": ["TextMapRU_0.json", "TextMapRU_1.json"],
}
DEFAULT_QUERIES = ["亚原子质能衍构核心", "三宝磨", "亥珀波瑞亚", "圣嗣", "霜月之子"]


def file_complete(path):
    if not os.path.exists(path):
        return False, "文件不存在"
    size = os.path.getsize(path)
    if size == 0:
        return False, "空文件"
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        last = f.read(1)
    if last != b"}":
        return False, f"末尾非 '}}'（末字节={last!r}，可能未下完）"
    return True, f"{size:,} 字节"


def load_lang(name):
    merged = {}
    for fn in FILES[name]:
        path = os.path.join(BASE, fn)
        ok, msg = file_complete(path)
        if not ok:
            raise RuntimeError(f"{fn}: {msg}")
        with open(path, encoding="utf-8") as f:
            merged.update(json.load(f))
    return merged


def show(h, data, out_langs, limit=200):
    txt = data["CHS"].get(h, "")
    if len(txt) > limit:
        txt = txt[:limit] + "…"
    print(f"  ── hash={h}")
    print(f"    CHS: {txt}")
    for L in out_langs:
        v = data[L].get(h, "<无对应条目>")
        if len(v) > limit:
            v = v[:limit] + "…"
        print(f"    {L} : {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="CHS,EN,DE,RU")
    ap.add_argument("--grep", nargs="*", default=None, help="子串检索关键词")
    ap.add_argument("--max", type=int, default=15, help="每个关键词最多展示条数")
    ap.add_argument("queries", nargs="*")
    args = ap.parse_args()

    langs = [x.strip().upper() for x in args.langs.split(",") if x.strip()]
    data = {}
    for lang in langs:
        try:
            data[lang] = load_lang(lang)
            print(f"[OK]   {lang}: {len(data[lang]):,} 条")
        except Exception as e:  # noqa: BLE001
            print(f"[跳过] {lang}: {e}")
    if "CHS" not in data:
        print("\nCHS 未载入，终止。")
        return
    out_langs = [L for L in langs if L != "CHS" and L in data]

    # ---- 子串检索模式 ----
    if args.grep:
        for kw in args.grep:
            print("\n" + "=" * 74)
            print(f"子串检索：含「{kw}」的条目")
            n = 0
            for h, t in data["CHS"].items():
                if kw in t:
                    n += 1
                    if n <= args.max:
                        show(h, data, out_langs)
            print(f"  ► 合计命中 {n} 条")
        return

    # ---- 精确反查模式 ----
    rev = {}
    for h, t in data["CHS"].items():
        rev.setdefault(t, []).append(h)
    print(f"\n中文反向索引：{len(rev):,} 个唯一文本")
    for q in (args.queries or DEFAULT_QUERIES):
        print("\n" + "=" * 74)
        print(f"精确反查：{q}")
        hits = rev.get(q)
        if not hits:
            print("  ✗ 未精确命中（该词多半只作为句子成分出现，请用 --grep 子串检索）")
            continue
        print(f"  ✓ 命中 {len(hits)} 个 hash：{hits[:5]}")
        for h in hits[:2]:
            show(h, data, out_langs)


if __name__ == "__main__":
    main()
