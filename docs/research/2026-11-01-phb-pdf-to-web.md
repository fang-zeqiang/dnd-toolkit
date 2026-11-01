# PHB 中译 PDF → 在线规则书

源文件：`5eDnD_玩家手册PHB_中译v1.6版.pdf`（256 页 A4，双栏，Illustrator 导出，有文字层与书签）。PDF 本身不进仓库。

## 产物（`/phb/`）

| 路径 | 内容 |
| --- | --- |
| `index.html` | 阅读器：书签目录、标题/法术名过滤、子串全文搜索、上下页、原版图切换。hash 路由 `#/p/<页>[/<锚点>][?q=<词>]` |
| `guide.html` | 建卡速查 + 角色草稿计算器（localStorage） |
| `pages/NNN.html` | 每页重排正文片段（fetch 注入） |
| `toc.js` | `PHB_TOC = {outline, heads, pages}`：PDF 书签 + 全书 1500+ 标题（含法术名）及锚点 |
| `search.js` | `PHB_TEXT`：每页纯文本，首次搜索时懒加载（约 1.1MB） |
| `img/NNN.jpg` | 原版页面图，120dpi q62（约 43MB） |

## 为什么这样做

- 全文搜索不用 Pagefind：中文子串匹配无需分词，256 页文本客户端直接扫，结果比分词更稳，且零依赖。
- 默认 `pdftotext` 会把左右栏逐行交错，所以改用 `pdftohtml -xml` 的坐标与字体：按中线（x=446）分栏，跨中线的元素形成全宽带（大表格），左右栏同一行都是多格的连续 ≥3 行也并为全宽表格；`#800000` 色 + 字号 ≥14 判为标题。
- 康熙部首（如 `⼒`）NFKC 规范化，否则搜「力量」漏结果。
- 重排有缺陷时（少数跨栏表格、侧栏框）以原版图为准，不手改重排结果。

## 重新生成

```bash
pdftohtml -xml -i -q phb.pdf /tmp/phbx            # 生成 /tmp/phbx.xml
python3 -I scripts/phb_convert.py /tmp/phbx.xml phb   # 覆盖 phb/pages、toc.js、search.js
pdftoppm -r 120 -jpeg -jpegopt quality=62 phb.pdf /tmp/pg   # 再改名为 phb/img/NNN.jpg
node tests/phb.test.js
```

`guide.html` 的规则数据是人工从原文摘录的（附页码），重新生成不会改动它。已知中译偏差：邪术师技能列表中译作「洞悉」，原版为 Investigation（调查），速查按原版并加注。
