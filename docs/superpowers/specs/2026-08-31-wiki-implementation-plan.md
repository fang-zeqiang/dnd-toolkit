# 5E 不全书 Wiki 实施方案

> 执行前必读: `CONTEXT.md`(术语)、`docs/adr/0001-wiki-pin-gate-edge-middleware.md`(门禁决策)、`docs/research/2026-08-31-chm-to-web-wiki.md`(调研依据)。
> 本方案是 grill 会话的定案产物, 所有决策已由用户拍板, 执行时不要重新发起讨论。

## 目标

把 `5E不全书 v2024.3.25.chm`(仓库根, 30MB)做成 `dnd.zeqiang.fun/wiki/` 下的自用在线 Wiki。iPad 跑团查询为主场景。一次性转换, 原书已停更, 不需要可重复脚本(转换过程用完即弃, 但过程中的一次性脚本可留在 /tmp)。

## 已定决策(不可重新讨论)

| 决策点 | 结论 |
|---|---|
| 访问控制 | PIN `8888`, Vercel Edge Middleware 拦 `/wiki/*`, 通过后种 30 天 cookie |
| 存储 | 全部产物进 git; chm 原文件不进 git(白名单制天然排除) |
| 阅读器 | 单壳 `wiki/index.html`: 左目录树 + 右 iframe, hash 路由 |
| 原书页面 | 除转码和 meta charset 修正外一字不动, 不重新格式化 |
| 查询 | 目录树标题/词条即时过滤 + Pagefind 全文搜索 |
| 入口 | 首页加第三张卡片; 工具页和首页保持公开 |
| 文件名 | 保留中文文件名, 不改名 |

## 关键事实(已探明, 不用再查)

- 解压后 113MB / 4432 文件 / 4119 个 html / 77 张图片(9.7MB)。
- 编码: 页面 meta 声明 gb2312, 实际按 **GB18030** 解码(超集, 保生僻字)。
- `.hhc`(目录树)和 `.hhk`(词条索引)也是 GBK 编码, 需先转码再解析。
- 全书仅 **3 个文件**含跨页 href, 且 href 是 GBK 原始字节 —— 整文件转码时自动随内容转为 UTF-8, 与磁盘 UTF-8 文件名对齐, **无需单独修链接**。
- 解压产物含 CHM 内部文件(`#IDXHDR`、`#STRINGS`、`$FIftiMain`、`$WW*` 等目录/文件), **不要**拷入 wiki 产物。
- 本机已装 `p7zip`(命令 `7z`)。Pagefind 未装。
- Vercel CLI 部署上限 15,000 源文件; 现有站 + wiki(~4500) + pagefind 索引分片(估 4000-5000) 合计接近 10k-11k, 安全但执行后要实际确认总数。

## 目录布局(产物)

```
/
├── middleware.ts            ← 全站唯一非静态组件 (见 ADR-0001)
├── index.html               ← 改: 加第三张卡片
├── wiki/
│   ├── index.html           ← 阅读器壳 (零依赖 vanilla JS)
│   ├── pin.html             ← PIN 输入页 (middleware 放行此页)
│   ├── toc.js               ← 由 .hhc + .hhk 生成的导航数据 (JS 赋值格式, 便于 file:// 调试可选 JSON)
│   ├── pagefind/            ← Pagefind 生成的索引与 UI 资源
│   └── book/                ← 4119 页原书 + 77 图, 转码后, 目录结构原样
```

## 实施步骤

### 1. 解压与转码

1. `7z x` 解压 chm 到临时目录; 剔除 `#*`、`$*` 内部文件和 `template2` 等非内容目录(逐一确认后剔除, 拿不准的保留)。
2. 全部 `.htm/.html/.hhc/.hhk` 以 GB18030→UTF-8 转码(iconv 或 Python `open(encoding='gb18030')`)。个别文件若解码失败, 记录清单、fallback `errors='replace'` 并人工抽查。
3. 每页 HTML 做且仅做三处机械修正:
   - `<meta ... charset=gb2312>` → `charset=utf-8`(各种写法用正则覆盖);
   - `<html>` → `<html lang="zh">`(Pagefind extended 中文分词依赖);
   - 移除文件头 `<!-- coding: gbk -->` 注释(可选)。
   除此之外**不动任何字节**。
4. 产物拷入 `wiki/book/`, 保留原目录层级与中文文件名。

### 2. 导航数据生成

1. 解析转码后的 `.hhc`: `<OBJECT type="text/sitemap">` 的 `Name`/`Local` param, `<UL>` 嵌套即层级。生成树形结构。注意: 部分节点 `Local` 为空(纯分组节点)。
2. 解析 `.hhk` 词条(扁平: 词条名→页面路径), 合并进同一份数据, 标记来源(目录 vs 索引), 供过滤框统一检索。
3. 输出 `wiki/toc.js`(如 `window.WIKI_TOC = {...}`)。路径统一相对 `wiki/book/`。
4. 校验: 随机抽 20 个 `Local` 路径确认文件真实存在; 统计死链数, >1% 需排查(大小写、路径分隔符)。

### 3. 阅读器壳 `wiki/index.html`

- 零依赖 vanilla JS + 内联样式, 视觉沿用 `index.html` 的 `:root` 变量体系(`--gold: #c9a45c` 等深色奇幻风)。
- 布局: 左侧目录树(可折叠层级) + 右侧 `<iframe>`。**iPad 优先**: 侧栏做成可收起抽屉, 触控目标 ≥44px, 横竖屏都可用; 桌面端侧栏常驻。
- hash 路由: `wiki/#/怪物图鉴/xxx.html` ↔ iframe src 双向同步(iframe 内点击跨页链接时用 `load` 事件读 `contentWindow.location` 回写 hash — 同源可行)。刷新/收藏/分享链接均可恢复页面。
- 顶部过滤框: 输入即过滤目录树节点 + `.hhk` 词条, 命中高亮, 点击跳页。纯客户端, 数据即 `toc.js`。
- 顶部另设 Pagefind 全文搜索入口(见步骤 4)。
- 尊重 `prefers-reduced-motion`, 与现有页面一致。

### 4. Pagefind 全文搜索

1. 下载 Pagefind **extended** 版静态二进制(内置中文分词), 不引入 npm/构建链。
2. 对 `wiki/book/` 跑索引, 产物输出到 `wiki/pagefind/`。
3. 阅读器壳里挂 Pagefind 默认 UI(其 JS/CSS 由 pagefind 产物自带, 仍属"纯静态产物", 不违背零依赖约束)。
4. 验证: 搜"火球术"、"豁免"等词有结果且点击可跳转; 中文分词正常(非整句才命中)。

### 5. PIN 门禁 `middleware.ts`

- 仓库根 `middleware.ts`, standalone Vercel Edge Middleware(Web 标准 Request/Response, **无 npm 依赖**)。
- `config.matcher = ['/wiki/:path*']`; 放行 `/wiki/pin.html`(及其所需资源)。
- 逻辑: cookie `wiki_auth` 等于预期 token → 放行; 否则 302 到 `/wiki/pin.html?back=<原路径>`。
- `pin.html`: 输入 PIN, JS 校验 `8888`, 正确则 `document.cookie` 种 30 天 token 并跳回 `back`。token 用固定随机串(如一段 hex), 硬编码即可 —— 定位是防君子(见 ADR-0001)。
- 验证: 无 cookie 直接请求 `wiki/book/` 下任意深层 html 必须被 302, 不能只拦 `wiki/index.html`。

### 6. 首页入口

`index.html` 加第三张卡片, 沿用现有卡片结构/样式(双列变三列或换行, 移动端保持单列), 文案风格与现有两张一致。链接 `/wiki/`。

### 7. .gitignore 白名单

现行"全忽略+白名单"制, 需追加允许:
```
!middleware.ts
!wiki/
!wiki/**
!CONTEXT.md
!docs/adr/
!docs/adr/**
!docs/research/
!docs/research/**
```
(具体语法对齐现有 gitignore 写法; 确认 chm 原文件仍被忽略。)

### 8. 部署与验收(按既有 spec 流程: 本地 → Preview → Production)

1. 本地 `python3 -m http.server 8000` 全量点验(middleware 本地不生效, 只验内容/导航/搜索)。
2. `vercel` 出 Preview, 在 Preview 上验:
   - PIN 门禁: 无 cookie 访问 `/wiki/` 和深层页均 302; 输对 PIN 后畅通; 30 天 cookie 生效。
   - iPad Safari 实机: 抽屉、触控、iframe 滚动、hash 恢复。
   - 中文 URL 百分号转码后正常打开; 随机抽 30 页无乱码。
   - Pagefind 中文搜索可用。
   - 工具页 `/tavern/`、`/map/` 与首页不受 middleware 影响。
   - 部署文件总数 < 15,000。
3. git commit(注意 113MB+ 首次 push 较慢属正常), Production 发布。
4. 回滚策略沿用既有 spec: Vercel 部署历史一键回滚。

## 明确不做

- 不改写原书页面样式/结构; 不转 Markdown(调研证实表格必坏)。
- 不做飞书图床(附件 URL 签名过期, 无法热链 —— 已否决)。
- 不留可重复转换脚本(原书停更)。
- 不做强安全(限速、服务端 session 等)。
