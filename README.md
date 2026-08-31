# DND Toolkit

一组零依赖、可直接在浏览器运行的 DND 桌边工具。

## 在线工具

生产地址：<https://dnd.zeqiang.fun>

| 路由 | 用途 |
| --- | --- |
| `/` | 工具选择首页 |
| `/tavern/` | 巨魔颅骨酒馆经营工具 |
| `/map/` | GRIDBOUND 战图印制坊 |

## 本地预览

```bash
git clone https://github.com/fang-zeqiang/dnd-toolkit.git
cd dnd-toolkit
python3 -m http.server 8000
```

打开 <http://127.0.0.1:8000>。请使用本地服务器，不要直接双击 HTML。

## 参与共建

1. Fork `fang-zeqiang/dnd-toolkit`。
2. 克隆自己的 Fork 并创建独立分支。
3. 只修改目标 HTML，启动本地服务器验证。
4. 提交并推送分支，向 `fang-zeqiang/dnd-toolkit:main` 发起 PR。
5. 视觉改动请附修改前后截图。

```bash
git clone https://github.com/<你的账号>/dnd-toolkit.git
cd dnd-toolkit
git switch -c style/improve-tool-cards
git add index.html
git commit -m "style: improve toolkit cards"
git push -u origin style/improve-tool-cards
```

## 样式改造建议

项目没有 CSS 构建流程；样式位于各 HTML 的 `<style>` 中。首页颜色集中在 `:root`：

```css
:root {
  --gold: #c9a45c;
  --gold-bright: #f0cf83;
}
```

保持 PR 聚焦。修改首页时不要格式化两个大型工具 HTML，也不要顺带修改工具内部逻辑。

## PR 自检清单

- [ ] `/`、`/tavern/`、`/map/` 均返回 HTTP 200
- [ ] 桌面端和移动端均可正常使用
- [ ] 首页两个入口跳转正确
- [ ] 酒馆主要交互和本地存档正常
- [ ] 战图可选择图片、预览并导出
- [ ] 浏览器控制台没有新增错误
- [ ] 没有引入第三方脚本、外部依赖或构建工具
- [ ] 没有提交 PDF、XLSX、ZIP、角色资料、私人图片、密钥、Token 或 `.vercel/`

## 项目约束

- 仅使用静态 HTML、内联 CSS 和原生 JavaScript。
- 两个工具彼此独立；非必要不改其业务逻辑。
- 测试地图、导出文件和私密跑团资料不得进入仓库。

## 提交信息

使用 `feat:`、`fix:`、`style:`、`docs:` 或 `refactor:` 前缀。
