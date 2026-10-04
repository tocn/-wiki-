---
title: Map维护
pageid: 16782
source: https://wiki.biligame.com/ys/Map维护
fetched_at: 2026-10-04T17:06:31+00:00
---

## 主表

Data:Map/type/json（保护）：用于记录目前所有点位的具体信息。这个就是点位列表的配置数据页面，mapc根据他来生成点位列表和统计列表。

字段说明：

| 字段 | 数据类型 | 例子 | 说明 |
| --- | --- | --- | --- |
| type | 文本 | "默认" | 点位的上级分类名称。用于区分甜甜花是"植物"还是"蒙德特产" |
| markType | 数字 | "201" | 点位的类别id。用于区分是甜甜花还是蒲公英（当前表内不可重复） |
| markTypeName | 文本 | "七天神像" | 点位类别的名称 |
| icon | 图片文件名 | "七天神像.png" or "https://patchwiki.biligame.com/images/ys/b/b5/oqhw4hrl93egmab7t9spzhlxvpph7mf.png" | 点位图片的地址 |
| defaultShow | 布尔值 | “1”or“0” | 打开地图默认显示为"1"，默认不显示为"0" |
| collectible | 布尔值 | true or 缺省 | 该点位可以进行标记计数则需要该字段 |
| index | 数字 | 201 | 预留字段暂无用 |

### 调用全部的点位

为了把散落在编号页面的点位数据集中在一个有缓存的实际页面，地图工具只请求这一个页面就可以拿到全部的点位数据。

因为这个页面相当于调用所有点位的信息，当点位信息总量超过一个wiki页面的容量上限（2M）的时候，就需要使用多页面分流信息以避免地图崩掉。

点位较少的时候（总点位数量≤7000）可以使用这个页面Data:MapHD/point.json，这个页面可以**自动维护**。

```
<div id="mapPointData" style="display:none">{ {{#arraymap: {{#ask:[[分类:地图点位数据]][[~Data:MapHD/*]]|link=none}} | , | @ | {{#replace: @ | Data:MapHD/type/ | }}:{{:@/json}} | ,}} }</div>
```

但是一旦点位特别多（总点位数量＞7000）就会因为超出页面可调用的模板上限（MediaWiki机制导致）使地图功能报错，所以在点位较多的情况下就需要**手动维护**这样的页面：Data:Map/point.json。

如果点位过多还需要拆表，例如创建一个Data:Map/point2.json，以此类推。

通过Widget:Map3/main页面的`dataList`字段增加点位表，如下：

```
var $ready = function () {
$.fn.swipe = swipe;
$("#map-wrap").swipe();
mapApi.set({game: 'ys', site: mw.config.get("wgGameName"), dataPrefix: 'Data:Map'})
ko.applyBindings(mapModel = new MapModel(mapData.default = {
game: 'ys',
site: mw.config.get("wgGameName"),
mapid: 'map3',
dataPrefix: 'Data:Map',
mapCenter: [-51.085105, 38.289228],
srcVersion: '3.0.13',
isPhone: window.innerWidth < 540,
toolbox: mw.config.get("wgUserGroups").indexOf("sysop") !== -1,
dataList: ["point.json", "point2.json"]
}));
```

### 关于分类排序

打开主表时可以看到一个默认的从上到下的排序，加入新的点位时请放到对应的分类里即可。

## 点位表

Data:Map/type/82（点位类型markType）/json：用于记录一个类别的点位的所有点个点位的数据。

字段说明：

| 字段 | 数据类型 | 例子 | 说明 |
| --- | --- | --- | --- |
| type | 文本 | "ys" |
| markType | 数字 | "82" | 点位的类别id。用于区分是甜甜花还是蒲公英（当前表内不可重复） |
| id | 文本 | "8z4xio6m3l" | 一个点位的唯一id。用于区分是哪一个甜甜花。 |
| icon | 图片文件名 | "魔晶矿.png" or "https://patchwiki.biligame.com/images/ys/b/b5/oqhw4hrl93egmab7t9spzhlxvpph7mf.png" | 点位图片的地址（已弃用） |
| point | 数字 | {"lng":"-16.258611","lat":"-11.778788"} | 点位在地图上的坐标数据（不需要进行人工维护） |
| title | 文本 | "魔晶矿" | 该点位的标题名称（已弃用） |
| content | 文本 | "位于石头屏障之后" | 该点位的描述文字（已弃用） |
| imageLink | 图片文件名 | 该点位的描述图片（已弃用） |
| wikiLink | 链接地址 | 该点位跳转的WIKI页面地址（已弃用） |
| videoLink | 链接地址 | 该点位上的说明视频地址（已弃用） |

## 单个点位页面

Data:Map/point/114xhifam3t(点位id)

## 用户个人点位表

用户:265262256/wikiYSMapData.json

## 区域范围表

Data:Map/蒙德.json
Data:Map/璃月.json
Data:Map/雪山.json
Data:Map/稻妻.json
