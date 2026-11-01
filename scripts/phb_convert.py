"""PHB PDF (pdftohtml -xml output) -> reflowed per-page HTML fragments + search/toc data.

usage: python3 -I convert.py phbx.xml outdir
"""
import html
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

XML, OUT = sys.argv[1], sys.argv[2]
root = ET.parse(XML).getroot()

MID = 446
FOOT_TOP = 1185
GAP_CELL = 9
MAROON = {'#800000', '#501d1e', '#7f0000', '#c00000', '#9b2d1f'}

fonts = {}


def inner_html(el):
    """Serialize text item children keeping <b>/<i>."""
    out = [html.escape(fix_radicals(el.text or ''))]
    for c in el:
        tag = c.tag if c.tag in ('b', 'i') else None
        body = inner_html(c)
        out.append(f'<{tag}>{body}</{tag}>' if tag else body)
        out.append(html.escape(fix_radicals(c.tail or '')))
    return ''.join(out)


EXTRA = {'\u2ed4': '门', '\u2ea9': '王'}


def fix_radicals(s):
    s = ''.join(EXTRA.get(c, c) for c in s)
    return ''.join(unicodedata.normalize('NFKC', c) if '\u2e80' <= c <= '\u2fdf' else c for c in s)


def plain(el):
    return fix_radicals(''.join(el.itertext()))


class Item:
    __slots__ = ('top', 'left', 'width', 'height', 'right', 'font', 'html', 'text', 'size', 'color', 'bold')

    def __init__(self, el):
        self.top = int(el.get('top'))
        self.left = int(el.get('left'))
        self.width = int(el.get('width'))
        self.height = int(el.get('height'))
        self.right = self.left + self.width
        self.font = el.get('font')
        self.html = inner_html(el)
        self.text = plain(el)
        f = fonts.get(self.font, {})
        self.size = int(f.get('size', 12))
        self.color = f.get('color', '#000000').lower()
        self.bold = self.text.strip() != '' and all(
            (c.tag == 'b') for c in el) and len(list(el)) > 0 and not (el.text or '').strip()


def group_lines(items):
    items = sorted(items, key=lambda i: (i.top, i.left))
    lines = []
    for it in items:
        placed = False
        for ln in reversed(lines[-3:]):
            ref = ln[0]
            # same visual line: tops close, or vertical overlap with similar baseline
            if abs(it.top + it.height - (ref.top + ref.height)) <= 4 or abs(it.top - ref.top) <= 3:
                ln.append(it)
                placed = True
                break
        if not placed:
            lines.append([it])
    for ln in lines:
        ln.sort(key=lambda i: i.left)
    lines.sort(key=lambda ln: min(i.top for i in ln))
    return lines


def visible(ln):
    return [i for i in ln if i.text.strip()]


def cells(ln):
    vis = visible(ln)
    out = []
    for it in vis:
        if out and it.left - out[-1][-1].right < GAP_CELL:
            out[-1].append(it)
        else:
            out.append([it])
    return out


def is_heading(ln):
    vis = visible(ln)
    if not vis:
        return False
    if not all(i.color in MAROON for i in vis):
        return False
    return max(i.size for i in vis) >= 14


def heading_level(ln):
    s = max(i.size for i in visible(ln))
    if s >= 30:
        return 1
    if s >= 22:
        return 2
    if s >= 17:
        return 3
    return 4


def join_html(parts):
    out = ''
    prev_plain = ''
    for h, p in parts:
        if out and prev_plain and p and re.match(r'[A-Za-z0-9]', p[0]) and re.search(r'[A-Za-z0-9,.;:)]$', prev_plain):
            out += ' '
        out += h
        if p:
            prev_plain = p
    return out


def cell_html(cell):
    return join_html([(i.html.strip(), i.text.strip()) for i in cell]).replace('</b><b>', '').replace('</i><i>', '')


def line_html(ln):
    return join_html([(i.html, i.text) for i in ln]).replace('</b><b>', '').replace('</i><i>', '')


def render_column(lines, blocks):
    """Append (kind, html, text) blocks for one column of one band."""
    if not lines:
        return
    texty = [ln for ln in lines if visible(ln) and not is_heading(ln) and len(cells(ln)) < 2]
    col_left = min((visible(ln)[0].left for ln in texty), default=0)
    col_right = max((visible(ln)[-1].right for ln in texty), default=0)

    para = []  # list of lines
    table = []  # list of rows (list of cell html)
    prev_ln = None

    def flush_para():
        if para:
            h = join_html([(line_html(l).strip(), ''.join(i.text for i in l).strip()) for l in para])
            t = ''.join(''.join(i.text for i in l).strip() for l in para)
            if t.strip():
                blocks.append(('p', h, t))
            para.clear()

    def flush_table():
        if table:
            if len(table) == 1:
                blocks.append(('p', ' '.join(table[0][0]), ' '.join(table[0][1])))
            else:
                blocks.append(('table', [r[0] for r in table], ' / '.join(' '.join(r[1]) for r in table)))
            table.clear()

    for ln in lines:
        vis = visible(ln)
        if not vis:
            continue
        if is_heading(ln):
            flush_para()
            flush_table()
            h = cell_html(vis)
            lvl = f'h{heading_level(ln)}'
            txt = ''.join(i.text for i in vis).strip()
            if blocks and blocks[-1][0] == lvl and not re.search(r'[\u4e00-\u9fff]', txt):
                k, ph, pt = blocks.pop()
                blocks.append((k, ph + ' ' + h, pt + ' ' + txt))
                prev_ln = None
                continue
            blocks.append((f'h{heading_level(ln)}', h, ''.join(i.text for i in vis).strip()))
            prev_ln = None
            continue
        cs = cells(ln)
        if len(cs) >= 2:
            flush_para()
            table.append(([cell_html(c) for c in cs], [''.join(i.text for i in c).strip() for c in cs]))
            prev_ln = None
            continue
        flush_table()
        first = vis[0]
        new_para = False
        if prev_ln is None:
            new_para = True
        else:
            pv = visible(prev_ln)
            gap = first.top - pv[0].top
            line_h = max(i.height for i in pv)
            if first.left > col_left + 12:
                new_para = True
            elif pv[-1].right < col_right - 30:
                new_para = True
            elif gap > line_h * 2.3:
                new_para = True
            elif first.html.lstrip().startswith('<b>') and not pv[-1].html.rstrip().endswith('</b>'):
                new_para = True
        if new_para:
            flush_para()
        para.append(ln)
        prev_ln = ln
    flush_para()
    flush_table()


def page_blocks(page):
    items = []
    for el in page:
        if el.tag == 'fontspec':
            fonts[el.get('id')] = el.attrib
        elif el.tag == 'text':
            it = Item(el)
            if it.top >= FOOT_TOP and re.fullmatch(r'\s*\d+\s*', it.text):
                continue
            items.append(it)
    L, R, F = [], [], []
    for it in items:
        if not it.text.strip():
            (L if it.left < MID else R).append(it)
        elif it.left < MID - 6 and it.right > MID + 10:
            F.append(it)
        elif it.left < MID:
            L.append(it)
        else:
            R.append(it)
    left = [ln for ln in group_lines(L) if visible(ln)]
    right = [ln for ln in group_lines(R) if visible(ln)]
    full = [ln for ln in group_lines(F) if visible(ln)]
    # a straddling line absorbs column fragments sitting on the same row
    for ln in full:
        t = ln[0].top
        for col in (left, right):
            for other in [o for o in col if abs(o[0].top - t) <= 4]:
                ln.extend(other)
                col.remove(other)
        ln.sort(key=lambda i: i.left)
    # full-width tables without straddling cells: runs of row pairs that are both tabular
    pairs = []
    for i, ln in enumerate(left):
        if len(cells(ln)) < 2:
            continue
        for j, o in enumerate(right):
            if abs(o[0].top - ln[0].top) <= 4 and len(cells(o)) >= 2:
                pairs.append((i, j))
                break
    runs, cur = [], []
    for p in pairs:
        if cur and p[0] == cur[-1][0] + 1 and p[1] == cur[-1][1] + 1:
            cur.append(p)
        else:
            if len(cur) >= 3:
                runs.append(cur)
            cur = [p]
    if len(cur) >= 3:
        runs.append(cur)
    drop_l, drop_r = set(), set()
    for run in runs:
        for i, j in run:
            full.append(sorted(left[i] + right[j], key=lambda it: it.left))
            drop_l.add(i)
            drop_r.add(j)
    left = [ln for i, ln in enumerate(left) if i not in drop_l]
    right = [ln for j, ln in enumerate(right) if j not in drop_r]
    really_full = full
    left.sort(key=lambda ln: ln[0].top)
    right.sort(key=lambda ln: ln[0].top)
    really_full.sort(key=lambda ln: ln[0].top)

    # bands split by full-width runs
    blocks = []
    cuts = []
    run = []
    for ln in really_full:
        if run and ln[0].top - run[-1][0].top > 40:
            cuts.append(run)
            run = []
        run.append(ln)
    if run:
        cuts.append(run)
    y = -1
    for run in cuts + [None]:
        y_end = run[0][0].top if run else 10 ** 9
        render_column([ln for ln in left if y <= ln[0].top < y_end], blocks)
        render_column([ln for ln in right if y <= ln[0].top < y_end], blocks)
        if run:
            render_column(run, blocks)
            y = run[-1][0].top + 1
    return blocks


def block_to_html(kind, h, page_no, idx):
    if kind == 'table':
        rows = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in h)
        return f'<div class="tbl"><table>{rows}</table></div>'
    if kind.startswith('h'):
        return f'<{kind} id="p{page_no}-{idx}">{h}</{kind}>'
    return f'<p>{h}</p>'


os.makedirs(os.path.join(OUT, 'pages'), exist_ok=True)
search = []
heads = []
for page in root.findall('page'):
    n = int(page.get('number'))
    blocks = page_blocks(page)
    parts = []
    texts = []
    for idx, (kind, h, t) in enumerate(blocks):
        parts.append(block_to_html(kind, h, n, idx))
        texts.append(t)
        if kind in ('h1', 'h2', 'h3', 'h4') and t:
            heads.append([re.sub(r'\s+', ' ', t), n, f'p{n}-{idx}', int(kind[1])])
    with open(os.path.join(OUT, 'pages', f'{n:03d}.html'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    search.append(re.sub(r'[ \t]+', ' ', '\n'.join(texts)))


def outline(o):
    res = []
    for el in o:
        if el.tag == 'item':
            res.append({'name': ''.join(el.itertext()).strip(), 'page': int(el.get('page')), 'children': []})
        elif el.tag == 'outline' and res:
            res[-1]['children'] = outline(el)
        elif el.tag == 'outline':
            res.extend(outline(el))
    return res


toc = []
for o in root.findall('outline'):
    toc.extend(outline(o))

with open(os.path.join(OUT, 'toc.js'), 'w', encoding='utf-8') as f:
    f.write('window.PHB_TOC = ')
    json.dump({'outline': toc, 'heads': heads, 'pages': len(search)}, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
with open(os.path.join(OUT, 'search.js'), 'w', encoding='utf-8') as f:
    f.write('window.PHB_TEXT = ')
    json.dump(search, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
print('pages', len(search), 'heads', len(heads))
