# 调研报告: CHM 文件线上化为现代 Web Wiki 的工具与最佳实践

- 日期: 2026-08-31
- 背景: 本项目需将中文 GBK 编码的 D&D 规则书 CHM (4119 页 / 103MB HTML) 部署为 Vercel 上的零依赖纯静态站, 已定方案为"解压 + 转 UTF-8 + iframe 阅读器壳"。本报告验证该方案并调研替代轮子。
- 方法: 所有关键结论均追溯至一手来源 (官方文档 / 源码仓库 / 格式规范 / 包注册表元数据), 来源 URL 附在每条结论后。GitHub 仓库活跃度数据来自 GitHub REST API 实测 (2026-08-31)。

---

## 0. 前置事实: CHM 格式与编码的关系

- CHM 是微软专有格式: 一组 HTML 页面 + 索引 (.hhk) + 目录 (.hhc), 以 LZX 压缩打包为二进制容器 (ITSS)。来源: [Wikipedia: Microsoft Compiled HTML Help](https://en.wikipedia.org/wiki/Microsoft_Compiled_HTML_Help) (二级来源, 仅作概述; 格式细节见下)。
- 格式无官方公开规范, 事实标准是社区逆向的 "Unofficial CHM Specification" (nongnu chmspec 项目)。其中明确: `#SYSTEM` 内部文件的 code 4 条目存储 HHP 工程的 **LCID** (locale ID), 全文检索索引 (`$FIftiMain`) 头部存储 **Windows code page identifier** 和 LCID。来源: [nongnu chmspec — Internal file formats](https://www.nongnu.org/chmspec/latest/Internal.html), [项目主页](https://savannah.nongnu.org/projects/chmspec/)。
- 关键推论 (已由规范验证): **CHM 容器内的 HTML 以原始字节存储, LZX 只是无损压缩**。GBK 编码的 CHM 解压后得到的就是 GBK 字节流 — 所以"任何解包工具 + iconv 转 UTF-8"这条路在格式层面无损、无坑, 编码问题与解包工具无关, 只取决于解包后的转码步骤。

---

## 1. 方向一: 成熟的 CHM → HTML / 静态站转换工具

### 1.1 chmlib / extract_chmLib (C 库, 事实标准底层)

- chmlib 是 Jed Wing 写的 ITSS/CHM 读取 C 库, `extract_chmLib` 是其自带的整包解压示例程序。**上游已死**: 原主页 http://www.jedrea.com/chmlib/ 现返回 404 (本次实测), Debian 包追踪器也报 watch 文件因 404 无法探测新版本, Debian 至今发行的仍是 **0.40a** (上游 0.40 发布于 2009 年)。来源: [Debian tracker: chmlib](https://tracker.debian.org/pkg/chmlib), 上游镜像 [github.com/jedwing/CHMLib](https://github.com/jedwing/CHMLib)。
- 编码: chmlib 只做容器解包, 输出原始字节, 不做任何字符集转换 — 对 GBK 内容是"透传", 无损也无帮助。
- 结论: 功能稳定但 17 年无维护; 作为一次性离线解包工具仍可用, 不宜作为长期依赖。

### 1.2 7-Zip 解包

- 7-Zip 官方将 CHM 列入 "Unpacking only" 支持格式 (`7z x file.chm` 即可整包解出)。来源: [7-zip.org 首页格式列表](https://www.7-zip.org/) ("Unpacking only: APFS, AR, ARJ, CAB, **CHM**, ..."), [7-Zip 文档 Supported formats](https://documentation.help/7-Zip/formats.htm) (该页并注明 CHM/CAB 格式描述来自 Matthew Russotto)。
- 7-Zip 持续活跃维护, 是**目前最省事、最可靠的 CHM 解包途径**; 同样输出原始 GBK 字节, 转码需自行 iconv。
- 佐证其工程可行性: 活跃项目 DTDucas/chm-converter 就是"7-Zip 解包 + chardet 编码探测"架构 (见 1.6)。

### 1.3 calibre 的 CHM 输入插件

- calibre 官方支持 CHM 作为输入格式, 转换管线为 "CHM 输入插件 → XHTML → 输出插件"。来源: [calibre FAQ (输入格式列表)](https://manual.calibre-ebook.com/faq.html), [E-book conversion 管线文档](https://manual.calibre-ebook.com/conversion.html)。
- 编码处理 (源码级验证): `chm_input.py` 使用内置 `CHMReader`, 编码回退链为 `self._chm_reader.get_encoding() or options.input_encoding or 'cp1252'`, 即**自动探测 CHM 内编码, 可用 `--input-encoding` 显式指定 GBK, 兜底 cp1252**; 并有"已转 UTF-8 则调整编码"的处理。来源: [calibre 源码 chm_input.py](https://github.com/kovidgoyal/calibre/blob/master/src/calibre/ebooks/conversion/plugins/chm_input.py)。
- 定位: calibre 目标是产出 EPUB/PDF 等电子书, 会重排 HTML, **不适合**"保留原始 HTML 建站"路线, 但它证明了 GBK CHM 的自动编码探测是成熟做法。calibre 本身活跃维护 (2026 年仍在发版, 见其 manual 版本号 9.x)。

### 1.4 xCHM

- xCHM 是基于 CHMLIB + wxWidgets 的跨平台 GPL **纯查看器**, README 未提供 HTML 导出/转换能力。仓库活跃 (最后 push 2026-06-25, 158 stars, GitHub API 实测)。来源: [github.com/rzvncj/xCHM](https://github.com/rzvncj/xCHM)。
- 结论: 与"线上化"无关, 排除。

### 1.5 pychm / archmage (Python 生态)

- pychm 是 CHMLIB 的官方 Python 绑定, 自述**处于 maintenance mode, 只接受安全和 bug 修复**; 其 `chm.extra` 模块提供全文检索和**编码探测**工具函数。依赖系统安装的 C 版 CHMlib。来源: [github.com/dottedmag/pychm](https://github.com/dottedmag/pychm), [PyPI: pychm](https://pypi.org/project/pychm/)。
- archmage (同一维护者) 基于 pychm, 官方 README: "arCHMage converts CHM files to HTML, plain text and PDF", 支持 `archmage -x file.chm outdir` 一键解压。最后 push 2025-06 (GitHub API 实测), 属低频维护。来源: [github.com/dottedmag/archmage README](https://github.com/dottedmag/archmage)。
- 结论: archmage 是"CHM→HTML 目录"最接近现成的开源 CLI, 但整条链 (chmlib→pychm→archmage) 都是维护模式。

### 1.6 chm2web 与新兴替代

- chm2web (A!K Research Labs) 是历史上专做 "CHM → 浏览器可用 HTML 帮助站" 的商业 Windows 工具。**官网 chm2web.aklabs.com 已无法访问** (本次 curl 实测连接失败), 软件仅存于 Internet Archive 与下载站镜像, 最新版本停在 2.8x。来源: [Internet Archive 存档页](https://archive.org/details/tucows_269862_chm2web), [SnapFiles 页面 (标注 "currently not available")](https://www.snapfiles.com/get/chm2web.html)。结论: 已死, 排除。
- **DTDucas/chm-converter** (Python, 101 stars, 最后 push 2026-08-25, GitHub API 实测): CHM → Markdown 转换器, 架构为 7-Zip 解包 + 自动编码探测。README 明确: "Auto encoding detection — handles UTF-8, GB18030, **GBK, GB2312**, and more via chardet", 并宣称 "Async + batched processing ... prevent memory overflow on large CHM files (**6000+ pages**)"。来源: [github.com/DTDucas/chm-converter README](https://github.com/DTDucas/chm-converter)。这是目前唯一**明确宣称支持 GBK/GB2312 且规模覆盖 4000+ 页**的活跃开源工具 — 但它产出 Markdown, 属"重构"路线 (见方向四)。

### 方向一小结

| 工具 | 类型 | 维护状态 | GBK 处理 |
|---|---|---|---|
| chmlib/extract_chmLib | C 解包库 | 上游死 (0.40a, 2009) | 字节透传, 不转码 |
| 7-Zip | 通用解包 | 活跃 | 字节透传, 不转码 |
| calibre CHM 输入 | 转电子书 | 活跃 | 自动探测 + 可指定, 兜底 cp1252 |
| xCHM | 桌面查看器 | 活跃 | 不适用 (非转换器) |
| pychm/archmage | Python 解包/转 HTML | 维护模式 | chm.extra 有编码探测 |
| chm2web | 商业 CHM→Web | 已死 | 不可考 |
| DTDucas/chm-converter | CHM→Markdown | 活跃 (2026-08) | 明确支持 GBK/GB2312/GB18030 |

---

## 2. 方向二: 纯前端 JS 直接解析/渲染 .chm 的可行性

### 2.1 生态盘点结论: 没有成熟项目

- GitHub 仓库搜索 `chm parser` 全量仅 16 个结果, 其中与 CHM 格式真正相关且非 Java/PHP 的**为零**; 唯一名字像 JS 方案的 cleverdb/chm 实为 **Java** 项目 (GitHub API languages 实测: `{"Java": 10199}`), 1 star, 2018 年后无活动。来源: GitHub Search API 实测 (2026-08-31), [github.com/cleverdb/chm](https://github.com/cleverdb/chm)。
- 以 `chmjs` / `chm.js` / `js-chm` / "chm wasm viewer" 等关键词的多轮搜索均未发现任何有社区基础的浏览器端 CHM 解析器; 也未发现 chmlib 的 Emscripten/WASM 移植。曾有的"浏览器看 CHM"方案都是**服务端解包**: jchmlib (Java, 内置 web server, 2017 年停更) 和 CHMBrowser (IIS/.NET Http Handler)。来源: [github.com/chimenchen/jchmlib](https://github.com/chimenchen/jchmlib), [github.com/mveteanu/CHMBrowser](https://github.com/mveteanu/CHMBrowser)。

### 2.2 唯一例外: chmlib-ts (2026 年新出的纯 TS 移植)

- npm 上 2026 年出现了 `chmlib-ts` (v0.3.0, 2026-04): "A pure TypeScript library for reading Microsoft HTML Help (.chm) archives. Port of chmlib by Jed Wing, with **LZX decompression derived from cabextract** by Stuart Caie"。API 支持 `chmReaderFromBuffer(uint8Array)`, 即理论上可在浏览器内从 ArrayBuffer 解 CHM; 提供 `#SYSTEM`/.hhc/.hhk 解析和 `--charset` 覆盖自动探测。LGPL-2.1。来源: [npm registry: chmlib-ts](https://registry.npmjs.org/chmlib-ts) (README 全文实测获取)。
- 成熟度评估: 仅 3 个版本 (0.1.0→0.3.0), package.json **未填 repository 字段** (无法审源码仓库), 无社区使用记录。其下游 `@chm-md/*` 工具链 (见 4.2) 仓库仅 10 commits / 0 stars。**技术上证明了"浏览器解 CHM"可行, 工程上不足以托付生产**。
- 可行性判断: LZX 解压在 JS 里可实现 (chmlib-ts 已做), 但对本项目场景 (103MB 单文件), 浏览器端方案意味着用户每次访问都要下载整个 103MB CHM 再在内存解压 — 相比预解压为静态文件 + CDN 按页加载, **网络与内存成本完全不成立**。浏览器内解析只适合"用户上传本地 CHM 即时预览"这类工具场景。

---

## 3. 方向三: 4000+ 页 / 100MB+ 存量 HTML 做在线 Wiki 的最佳实践

### 3.1 静态站生成器导入存量 HTML: 官方均不支持"HTML 作为内容页"

- **MkDocs** 官方文档明确: "MkDocs pages **must be authored in Markdown**"; 非 Markdown 文件的处理是 "Any files which are not identified as Markdown files ... are **copied by MkDocs to the built site unaltered**" — 即 HTML 只能当静态资产原样复制, 不进导航/搜索/主题。来源: [MkDocs: Writing your docs](https://www.mkdocs.org/user-guide/writing-your-docs/)。
- **Docusaurus** docs 插件的定位是 "organize **Markdown** files in a hierarchical format" (支持 MDX); 存量 HTML 只能放 `static/` 目录: "Every file you put into that directory will be copied into the root of the generated build folder with the directory hierarchy preserved" — 同样是原样复制、不融入站点。来源: [Docusaurus: Docs Introduction](https://docusaurus.io/docs/docs-introduction), [Docusaurus: Static Assets](https://docusaurus.io/docs/static-assets)。
- **VitePress** 同理, `public` 目录: "Assets placed in `public` will be copied to the root of the output directory **as-is**"。来源: [VitePress: Asset Handling](https://vitepress.dev/guide/asset-handling#the-public-directory)。
- 结论: 三大主流 SSG 对"存量 HTML 当一等内容"支持度都是**零** — 引入它们只能得到"SSG 壳 + public 目录里 4119 个原样 HTML", 与本项目现方案 (自写阅读器壳 + 原样 HTML) 相比只多了 Node 构建链, 没有增益。要吃到 SSG 的导航/搜索/主题, 必须先 HTML→Markdown 重构 (方向四)。

### 3.2 客户端搜索: Pagefind 是该规模下的最优解 (官方数据)

- **Pagefind 规模数据 (官方首页原话)**: "Pagefind can run a full-text search on a **10,000 page site with a total network payload under 300kB**, including the Pagefind library itself"; 多数站点实际接近 100kB。4119 页在其设计目标之内。来源: [pagefind.app 首页](https://pagefind.app/)。
- **零构建工具兼容**: "Pagefind works with any static HTML output. All static site generators and website frameworks are supported, as long as the built HTML contains the content" — 它是**事后对构建产物 HTML 目录建索引**, 不介入构建。运行方式三选一: `npx pagefind --site <dir>`、`pip install 'pagefind[extended]'`、或**下载免依赖静态二进制** ("Pagefind is a static binary with no dynamic dependencies") — 完全兼容"零依赖纯静态站"约束 (索引是一次性离线步骤, 产物是纯静态 JS/wasm/索引分片)。来源: [pagefind.app](https://pagefind.app/), [Installing Pagefind](https://pagefind.app/docs/installation/)。
- **中文分词 (官方文档)**: Pagefind 有双发行版, **extended 版内置中日文专用分词** ("the extended release is a larger binary, but includes specialized support for indexing Chinese and Japanese pages"), npx 默认即下载 extended 版。官方多语言文档: 中文按无空格分词切分索引 (示例 `每個月都` → `每個`/`月`/`都`), 查询串也会被切分后匹配; 不支持中文 stemming。来源: [Pagefind: Multilingual search](https://pagefind.app/docs/multilingual/), [Installing Pagefind](https://pagefind.app/docs/installation/)。
- 注意事项: Pagefind 按 HTML `lang` 属性分语言索引 — GBK 原文件转 UTF-8 时应确保 `<html lang="zh">` 与 `<meta charset="utf-8">` 正确, 否则会落入默认英文索引 (来源同上 multilingual 文档)。

### 3.3 内存型 JS 搜索库的规模边界

- **MiniSearch** (官方 README): 适用于"the data to be indexed can **fit locally in the process memory**"; 索引是全量驻内存的 radix tree, 定位是移动端等内存受限场景的中小数据集。对 4119 页 × 数十 KB 正文, 需要把全部文本打包成一个大 JSON 下发并在内存建索引, 首屏成本远超 Pagefind 的分片按需加载。README 未提供中文分词。来源: [github.com/lucaong/minisearch](https://github.com/lucaong/minisearch)。
- **lunr.js**: 上游基本停更 (最后 push 2024-07, 版本停在 2.3.9, GitHub API 实测)。中文需 lunr-languages 插件: 浏览器端靠 `Intl.Segmenter` + CJK bigram ("there is no frontend fallback"), Node 端可选 `@node-rs/jieba` 提升质量; 插件 README 自述 bigram 方案"不如 Jieba 的精度与排序"。且 lunr 的预建索引是单一 JSON, 4000+ 页级别索引文件会非常大。来源: [github.com/olivernn/lunr.js](https://github.com/olivernn/lunr.js), [lunr-languages README](https://github.com/MihaiValentin/lunr-languages)。
- **Fuse.js**: 官方定位 "lightweight fuzzy-search library", 是对内存数组的模糊匹配而非倒排索引; 官方另推 "Fuse Cloud" 应对 "without the client-side overhead" 的场景, 侧面说明大数据集不是其设计目标。不适合全文检索 4000+ 页。来源: [fusejs.io](https://www.fusejs.io/)。
- 结论: 该规模下 minisearch/lunr/fuse 都要求"全量文本下发 + 全量内存索引", 只有 **Pagefind 的静态分片索引** (按需加载) 匹配 100MB 级内容 + 纯静态部署。

### 3.4 部署平台约束 (Vercel)

- Vercel 官方 Limits: CLI 部署**源文件上限 15,000 个** ("Deployments that contain more files than the limit will fail"), 构建**输出**文件数无上限。4119 个 HTML + 图片资产 + Pagefind 索引分片 (每页约 1 个分片文件) 合计可能逼近该数量级, 需要留意; Git 集成部署走构建输出则不受 15,000 源文件限制。来源: [vercel.com/docs/limits](https://vercel.com/docs/limits)。

---

## 4. 方向四: "保留原始 HTML" vs "转 Markdown 重构"

### 4.1 HTML→Markdown 转换工具在复杂表格上的硬伤 (一手来源)

- **Turndown** (11.4k stars, JS 生态事实标准): **核心不支持表格**, 表格靠 `turndown-plugin-gfm` 插件; 而该插件最后 push 停在 **2023-05**, 关于 colspan/rowspan 的改进 PR (#31 "Improved support of TABLE") 至今 open 未合并 — 即官方插件至今不能正确处理跨行跨列表格。来源: [github.com/mixmark-io/turndown](https://github.com/mixmark-io/turndown), [turndown-plugin-gfm PR #31](https://github.com/mixmark-io/turndown-plugin-gfm/pull/31) (GitHub API 实测: 该仓库 pushed 2023-05-19)。
- **Pandoc** (官方手册原文): 输出 Markdown 常用的 pipe table 明确规定 "The cells of pipe tables **cannot contain block elements** like paragraphs and lists, and **cannot span multiple lines**" — 即 rowspan/colspan/单元格内多段落一律无法用 pipe table 表达。能表达跨行跨列的只有 pandoc 自家 grid table 扩展 ("Cells can span multiple columns or rows"), 但 grid table 不是 GFM, GitHub/VitePress/Docusaurus 默认渲染器都不认。来源: [Pandoc User's Guide — Tables 节](https://pandoc.org/MANUAL.html#tables) (引文取自官方仓库 MANUAL.txt)。
- D&D 规则书 HTML 恰恰是复杂表格重灾区 (跨行表头、嵌套、合并单元格的属性表/职业表), 这两条一手证据直接命中。

### 4.2 社区实践的印证

- 走"转 Markdown"路线的两个现役项目都为表格问题留了逃生门:
  - chm-markdown-transpiler (`@chm-md/cli`, 基于 chmlib-ts + Turndown+GFM, 输出 VitePress 站): README 自认 "**Complex or spanned tables may remain as HTML with warnings**", 且提供 `--table-chrome strip|preserve|flatten` 三档策略。项目本身 10 commits / 0 stars, 极早期。来源: [github.com/josh-hemphill/chm-markdown-transpiler](https://github.com/josh-hemphill/chm-markdown-transpiler)。
  - DTDucas/chm-converter: 提供 "Table normalization" 后处理, 目标场景是喂 AI/向量库而非像素级还原排版。来源: [README](https://github.com/DTDucas/chm-converter)。
- 即: **社区里最认真的 CHM→Markdown 工具, 最终答案也是"复杂表格保留为内嵌 HTML"** — 等于承认对表格密集型内容, Markdown 化是有损/半途的。

### 4.3 两条路线对比结论

| | 保留原始 HTML | 转 Markdown 重构 |
|---|---|---|
| 内容保真 | 无损 (含表格/内联样式) | 复杂表格必然降级或回退为内嵌 HTML (Pandoc/Turndown 一手证据) |
| 一次性成本 | 解压 + iconv + 链接/资源路径修正 | 4119 页转换 + 人工抽查表格 |
| 长期收益 | 无统一主题, 靠壳层 CSS/iframe 隔离 | 可用 SSG 全家桶 (导航/暗色/移动端) |
| 搜索 | Pagefind 直接索引 HTML, 无需重构 | SSG 内置或 Pagefind 均可 |
| 适用判断 | 内容冻结的存量规则书: **优** | 内容需持续编辑演进时才值得 |

对"内容基本冻结、表格密集、追求保真"的规则书, 保留 HTML 是社区经验支持的稳妥选择; Markdown 化的收益 (统一主题、可编辑) 对冻结内容不成立, 而其成本 (表格降级) 恰好打在本内容的要害上。

---

## 对本项目方案的启示

现方案 = **7-Zip/chmlib 解压 → GBK 转 UTF-8 → 保留原始 HTML → iframe 阅读器壳 → Vercel 纯静态部署**。逐环节结论:

**被验证为正确/最优的环节:**

1. **"解压 + 转 UTF-8" 是唯一健壮路径**: CHM 格式规范证实 HTML 按原始字节存储, 解压即得 GBK 原文; 没有任何工具能"免解压"服务 Web (浏览器端解析无成熟轮子且 103MB 场景成本荒谬, 见方向二)。解包工具选 7-Zip (活跃维护) 优于 extract_chmLib (上游死); 转码建议按 GB18030 (GBK 超集) 解码以覆盖生僻字, 这是 DTDucas/chm-converter 的探测链 (GB18030→GBK→GB2312) 印证的做法。
2. **"保留原始 HTML 不转 Markdown" 对本内容是对的**: Pandoc 手册与 Turndown 插件现状证明复杂表格 Markdown 化必然降级; 社区最好的 CHM→Markdown 工具也把复杂表格回退为 HTML。规则书表格密集 + 内容冻结, 重构无收益。
3. **不引入 Docusaurus/VitePress/MkDocs 是对的**: 三者官方都只能把存量 HTML 当静态资产原样复制, 引入它们对本项目只增加构建链、无功能增益。"零依赖自写壳"不是妥协, 而是该场景的正解。
4. **没有更好的现成整站轮子**: 专职的 chm2web 已死; 唯一活跃的方向 (chm-markdown-transpiler) 走 Markdown 路线且极不成熟 (0 stars/10 commits)。

**有更好替代/需补强的环节:**

5. **搜索是现方案最大的缺口, Pagefind 是现成答案**: 官方数据 (10,000 页 / <300kB 网络载荷) 覆盖 4119 页规模; extended 版内置中文分词; 以独立静态二进制运行、产物纯静态, 不破坏"无构建工具"约束 (一次性离线建索引即可)。强烈建议在转码后跑一次 `pagefind --site <输出目录>`, 给阅读器壳加搜索框。前提: 转码时给每页写入 `<html lang="zh">` + `<meta charset="utf-8">`。fuse.js/minisearch/lunr 在此规模均不可行 (全量文本下发 + 内存索引)。
6. **iframe 壳可从 CHM 元数据免费获得导航**: .hhc (目录树) / .hhk (索引) 是 CHM 自带的结构化导航数据, archmage、chmlib-ts 等都能解析导出; 壳层侧边栏应从 .hhc 生成而非手工维护。
7. **留意 Vercel 15,000 源文件上限**: 4119 HTML + 图片 + Pagefind 每页索引分片可能逼近该数; 走 Git 集成/构建输出部署可规避 CLI 源文件限制。
8. **iframe 之外的备选**: 若未来想去掉 iframe (SEO/移动端体验), 可在离线管线中给每页 HTML 注入统一的 `<link>` 壳样式 + 顶部导航片段 — 仍是纯静态、零运行时依赖, 且 Pagefind 对这种"裸 HTML 站"同样适用。此为渐进增强项, 非必需。

---

## 附: 本报告引用的一手来源清单

- CHM 格式规范: https://www.nongnu.org/chmspec/latest/Internal.html / https://savannah.nongnu.org/projects/chmspec/
- chmlib: https://tracker.debian.org/pkg/chmlib / https://github.com/jedwing/CHMLib (原主页 jedrea.com/chmlib 已 404, 实测)
- 7-Zip: https://www.7-zip.org/ / https://documentation.help/7-Zip/formats.htm
- calibre: https://manual.calibre-ebook.com/faq.html / https://manual.calibre-ebook.com/conversion.html / https://github.com/kovidgoyal/calibre/blob/master/src/calibre/ebooks/conversion/plugins/chm_input.py
- xCHM: https://github.com/rzvncj/xCHM
- pychm / archmage: https://github.com/dottedmag/pychm / https://pypi.org/project/pychm/ / https://github.com/dottedmag/archmage
- chm2web (已死): https://archive.org/details/tucows_269862_chm2web / https://www.snapfiles.com/get/chm2web.html
- DTDucas/chm-converter: https://github.com/DTDucas/chm-converter
- chmlib-ts (npm): https://registry.npmjs.org/chmlib-ts
- chm-markdown-transpiler: https://github.com/josh-hemphill/chm-markdown-transpiler
- jchmlib / CHMBrowser (服务端方案): https://github.com/chimenchen/jchmlib / https://github.com/mveteanu/CHMBrowser
- MkDocs: https://www.mkdocs.org/user-guide/writing-your-docs/
- Docusaurus: https://docusaurus.io/docs/docs-introduction / https://docusaurus.io/docs/static-assets
- VitePress: https://vitepress.dev/guide/asset-handling
- Pagefind: https://pagefind.app/ / https://pagefind.app/docs/installation/ / https://pagefind.app/docs/multilingual/
- MiniSearch: https://github.com/lucaong/minisearch
- lunr.js / lunr-languages: https://github.com/olivernn/lunr.js / https://github.com/MihaiValentin/lunr-languages
- Fuse.js: https://www.fusejs.io/
- Pandoc 手册 (Tables): https://pandoc.org/MANUAL.html#tables
- Turndown / turndown-plugin-gfm: https://github.com/mixmark-io/turndown / https://github.com/mixmark-io/turndown-plugin-gfm/pull/31
- Vercel Limits: https://vercel.com/docs/limits
