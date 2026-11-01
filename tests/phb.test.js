const fs = require('fs');
const assert = require('assert/strict');
const vm = require('vm');

const load = (file, name) => {
  const ctx = { window: {} };
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), ctx);
  return ctx.window[name];
};

const toc = load('phb/toc.js', 'PHB_TOC');
const text = load('phb/search.js', 'PHB_TEXT');

assert.equal(toc.pages, 256);
assert.equal(text.length, 256);
for (let n = 1; n <= 256; n++) {
  const id = String(n).padStart(3, '0');
  assert.ok(fs.existsSync(`phb/pages/${id}.html`), `missing page ${id}`);
  assert.ok(fs.existsSync(`phb/img/${id}.jpg`), `missing image ${id}`);
}

// 搜索语料无康熙部首等异体字，常用词可搜到
assert.ok(!/[⺀-⿟]/.test(text.join('')));
assert.match(text[111], /力量13/);
assert.ok(toc.heads.some((h) => h[0].startsWith('火球术') && h[1] === 191));
assert.ok(toc.heads.some((h) => h[0].startsWith('魔法飞弹')));

// 双栏重排：野蛮人职业表完整成表，不与左栏正文混行
const p35 = fs.readFileSync('phb/pages/035.html', 'utf8');
assert.match(p35, /<td>20th<\/td><td>\+6<\/td><td>原初斗士<\/td>/);

// 入口、门禁、速查页
assert.match(fs.readFileSync('index.html', 'utf8'), /href="\/phb\/"/);
assert.match(fs.readFileSync('middleware.ts', 'utf8'), /"\/phb\/:path\*"/);
const guide = fs.readFileSync('phb/guide.html', 'utf8');
for (const s of ['角色草稿', '种族速查', '职业速查', '背景速查', '兼职先决条件']) assert.ok(guide.includes(s), s);
