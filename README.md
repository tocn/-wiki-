# 原神 Wiki 文本镜像

BWIKI 原神站(<https://wiki.biligame.com/ys>)的**纯文本镜像**。
只收录 wiki 正文,不纳管任何图片/音视频等媒体资源。

## 数据来源与合规

- 源站:wiki.biligame.com/ys(MediaWiki 1.37.0)
- 已核对 `robots.txt`:允许抓取 `/ys/` 下的条目页;仅取**主命名空间(ns=0)**,
  避开被声明禁止的 `模板:` / `文件:` / `特殊:` / `User:` / `MediaWiki:` 等命名空间。
- 请求间隔 0.8 秒,以 `stealthy_headers` 正常浏览器身份访问,不使用任何绕过手段。
- 站点由腾讯云 EdgeOne 防护,普通裸请求会返回 HTTP 567 拦截页;
  使用 scrapling 的 `Fetcher.get(..., stealthy_headers=True)` 可正常获取。

## 目录结构

```
data/
  pages.jsonl       # 阶段一:ns=0 全量清单(52,021 条,含地图点位)
  targets.jsonl     # 阶段二:过滤后的抓取目标(19,663 条)
  fetch_log.jsonl   # 阶段二:逐页抓取记录(pageid/状态/字节数/时间)
  md/               # ★ 最终交付物:清洗后的 Markdown,每页一个文件
  index.jsonl       # pageid <-> 标题 <-> 文件 映射
cache/
  raw/              # 原始渲染 HTML(体积大,不入库,可随时重跑生成)
scripts/
  01_list_pages.py    # 枚举 ns=0 全部条目
  02_fetch_content.py # 批量抓取渲染 HTML(限速 + 断点续跑)
  03_html_to_md.py    # 清洗并转换为 Markdown
  clean.py            # 清洗模块(HTML -> Markdown)
```

## 管线用法

```bash
PY="C:/Users/admin/.workbuddy/binaries/python/envs/scrapling/Scripts/python.exe"

$PY scripts/01_list_pages.py          # 1. 枚举条目
$PY scripts/02_fetch_content.py       # 2. 抓取(可重复执行以续跑;--limit N 试点)
$PY scripts/03_html_to_md.py          # 3. 转换为 Markdown
```

三个阶段都可重复执行:阶段二依据 `fetch_log.jsonl` 跳过已完成页,阶段三整体重算。

## 范围说明

ns=0 下共 52,021 条,其中 **32,358 条为 `Data:Map*` 地图点位数据**
(实测内容为「一张图片引用 + 数十字标签」,属地图标记而非文本),
按本项目「只收录 wikitxt」的定位**已排除**;实际抓取 **19,663 条**。

## 已知噪声

少量页面含计时器模板残留(如 `52020/11/11 6:00:0…`),属源站模板渲染产物,
未做去除以保持内容忠实。极短页面(如仅含版权声明)会被阶段三跳过。
