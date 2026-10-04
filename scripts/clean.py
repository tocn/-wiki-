#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BWIKI 渲染 HTML -> 干净 Markdown 的清洗模块。

设计依据(实测 wiki.biligame.com/ys 的 .mw-parser-output 子节点结构):
    [0]  无 class 的 div   -> 「阅/编/刷/历」+ 面包屑    丢弃
    [1]  hr                                             丢弃
    [2]  .bg-snm           -> 站务提示                  丢弃
    [3]  .map-dh           -> 顶部导航条                丢弃
    [4]  .toc              -> 目录                      丢弃
    [5+] 正文(表格/标题/段落)                         保留
    [尾] .navigation-not-searchable -> 站尾导航          丢弃
    [尾] <style>           -> 内联 CSS                  丢弃
"""
import re

from bs4 import BeautifulSoup
from markdownify import markdownify

# 整块丢弃的噪声选择器
DROP_SELECTORS = [
    "script", "style", "link", "meta", "noscript",
    "#bread-edit",                 # 阅/编/刷/历
    ".bg-snm",                     # 站务提示
    ".map-dh",                     # 顶部导航
    ".toc",                        # 目录
    ".navigation-not-searchable",  # 站尾导航
    ".mw-editsection",
    ".ys-collapse-explain",        # 「展开/折叠」UI 标签
    # 隐藏容器:源站用来存前端脚本读取的数据,读者不可见。
    # 典型如 #categoryData / #mapAreaData / #categoryDataExtension —— 内嵌交互地图
    # 的标记 JSON(markTypeName / geojson / icon),若不剔除会灌入大量坐标与图标 URL。
    ".hide",
    ".shade",
    # 内嵌交互地图应用本体(#map-div 包住 #onload / #app / #map-set)。
    # 其内容是 Vue 组件模板({{item.markTypeName}} 一类),既非正文也无法在
    # Markdown 中还原;源站以交互地图呈现,本镜像不收录地图,故整块剔除。
    "#map-div",
]

# 清理后仍需剔除的纯 UI 残留行
JUNK_LINES = {"展开/折叠", "折叠", "展开", "目录"}

_WS = re.compile(r"[ \t\u00a0\u200b]+")
_BLANKS = re.compile(r"\n{3,}")


def _alive(el) -> bool:
    """
    节点是否仍挂在树上。

    BeautifulSoup 的 decompose() 会连同后代一起移除,并把它们的 attrs 置为 None。
    若在遍历中删掉父节点,列表里残留的后代引用就会变成空壳,再调用 .get() 会抛
    AttributeError。所有剔除操作前都先过这道检查。
    """
    return el is not None and getattr(el, "attrs", None) is not None


def _drop(elements) -> int:
    """批量剔除节点,自动跳过已被祖先带走的空壳。返回实际剔除数。"""
    n = 0
    for el in elements:
        if _alive(el):
            el.decompose()
            n += 1
    return n


def clean(html: str) -> str:
    """把 MediaWiki 渲染后的 HTML 转成干净 Markdown。"""
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one(".mw-parser-output") or soup

    # 整页即数据页:正文直接以 JSON 开头(如 Map4 页面,通篇是地图标记 JSON)。
    # 这类页面没有可定位的容器(JSON 落在顶层 <p>),只能按内容判定。
    probe = main.get_text(" ", strip=True).lstrip()
    if probe.startswith('{"') or probe.startswith('[{"') or probe.startswith('[{"data"'):
        return ""

    for sel in DROP_SELECTORS:
        _drop(main.select(sel))

    # 内联 display:none 的节点读者同样看不到,一并剔除
    # (先收集完再删,避免边遍历边改树)
    _drop([el for el in main.find_all(style=True)
           if "display:none" in (el.get("style") or "").replace(" ", "").replace("\n", "").lower()])

    # 面包屑所在的无 class 首层 div:通过 #bread-edit 已删,这里处理残留的兄弟面包屑
    _drop([el for el in main.find_all("div", recursive=False)
           if "首页" in el.get_text(" ", strip=True) and len(el.get_text(strip=True)) < 60])

    # 清掉不含文本、也无图片的空节点
    _drop([el for el in main.find_all(True)
           if not el.get_text(strip=True) and el.name not in ("img", "br", "hr")])

    text = markdownify(str(main), heading_style="ATX", bullets="-", strip=["a", "img"])

    # 逐行清理:去首尾空白、丢弃纯 UI 残留行
    lines = []
    for ln in text.splitlines():
        s = _WS.sub(" ", ln).strip()
        if s in JUNK_LINES:
            continue
        lines.append(s)
    text = "\n".join(lines)
    text = _BLANKS.sub("\n\n", text)
    return text.strip()


# 非文本页面:机器数据与命名空间残留,不属于 wiki 正文
JUNK_TITLE_PREFIXES = (
    "Data:",      # 含全部 Data:Map* 地图点位,以及 Data:roleCompute/data 等 JSON 数据块
    "Uesr:",      # 源站拼写错误的用户页
    "Meta:",
    "Weight:",
    "Xp:",
    "编辑教程:",
    "旅行者酒馆:",
)


def is_junk_title(title: str) -> bool:
    """判断标题是否属于「非 wiki 文本」页面,应予排除。"""
    t = title.strip()
    if t.startswith(JUNK_TITLE_PREFIXES):
        return True
    if "http" in t.lower():          # 被误建为条目的外链
        return True
    return False


def safe_filename(title: str) -> str:
    """把页面标题转成 Windows 合法文件名。"""
    s = re.sub(r'[<>:"/\\|?*]', "_", title)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return (s or "untitled")[:150]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    src = sys.argv[1]
    out = clean(open(src, encoding="utf-8").read())
    print(f"清洗后长度: {len(out)}\n" + "=" * 60)
    print(out[:2000])
