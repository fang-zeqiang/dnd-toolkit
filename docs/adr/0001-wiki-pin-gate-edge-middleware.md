# Wiki 版权内容以 Edge Middleware PIN 门禁并入零依赖静态站

《5E 不全书》是受版权保护的 D&D 5e 中文民间翻译合集（4119 页），要以自用 Wiki 形式挂到公网站 `dnd.zeqiang.fun/wiki/` 下。本站的既定约束是零依赖纯静态（无框架、无构建步骤），但纯客户端 JS 的 PIN 弹窗是假保护——4000+ 个 HTML 文件本身仍公开可取，直链即可绕过。因此决定：在仓库根放一个 `middleware.ts`，用 Vercel Edge Middleware 拦截 `/wiki/*`，校验 cookie，未通过则跳 PIN 输入页（PIN `8888`，通过后种 30 天 cookie）。这是全站唯一的非静态组件，是对「不用框架/构建工具」原则的一次刻意例外——它是唯一既能保护全部文件、又不引入框架和构建步骤的方案。

## Considered Options

- **纯客户端 JS 门禁** — 零改动部署架构，但不保护文件本身，形同虚设，弃。
- **拆独立 Vercel 项目 + 子域名隔离** — 保护彻底，但多一套部署与域名要维护，弃。
- **Edge Middleware（选定）** — 约 20 行，Vercel 对纯静态项目原生支持，边缘层拦截全部路径。

## Consequences

- PIN 门禁的定位是「不对公网裸露」（防搜索引擎与路人），不是强安全；PIN 硬编码、无速率限制，均为刻意取舍。
- 工具页（`/tavern/`、`/map/`）与首页保持公开，middleware 的 matcher 只覆盖 `/wiki/*`。
- 未来若迁离 Vercel，此门禁需按新平台等价重做（如 Cloudflare Workers / nginx auth）。
