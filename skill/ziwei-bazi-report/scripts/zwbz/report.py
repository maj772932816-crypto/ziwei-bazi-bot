"""facts.json（排盘事实）+ narrative.json（模型写的分析）→ 一个可单独打开、可微信转发的 HTML 报告。

所有文字都先做 HTML 转义；排盘数据、核对表、命盘格子、大运大限和逐年表由程序生成，模型只负责解读文字。
"""
import html
import json

from .brief import daxian_rows
from .dataset import ATTRIBUTION
from .ziwei import BR

E = lambda s: html.escape(str(s if s is not None else ''), quote=True)  # noqa: E731
GOOD = ['左辅', '右弼', '文昌', '文曲', '天魁', '天钺', '禄存', '天马']
BAD = ['擎羊', '陀罗', '火星', '铃星', '地空', '地劫']
HUA_CLS = {'禄': 'lu', '权': 'quan', '科': 'ke', '忌': 'ji'}
AGREE_CLS = {'两边一致': 'ok', '高': 'ok', '已核对': 'ver', '中': 'mid', '只有八字': 'mid', '只有紫微': 'mid', '低': 'warn', '有分歧': 'warn'}

CSS = r'''
:root {
  --bg: #f4f5f8; --surface: #ffffff; --ink: #1c2130; --muted: #5d6478; --faint: #8b91a3; --line: #dfe2ea;
  --accent: #2f5d8a; --accent-soft: #e6eef7; --gold: #9a7420; --gold-soft: #f6efdc; --warn: #a4521c; --warn-soft: #fbeee4;
  --ok: #2f7d4f; --ok-soft: #e4f3ea; --lu: #2f7d4f; --quan: #3559b5; --ke: #9a7420; --ji: #b23a3a;
  --font-display: "Songti SC", "STSong", "Noto Serif SC", "SimSun", serif;
  --font-body: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Noto Sans SC", sans-serif;
  --measure: 40em;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #11141c; --surface: #181c27; --ink: #e3e6ee; --muted: #a3a9ba; --faint: #767d90; --line: #2a3040;
  --accent: #8db5de; --accent-soft: #1d2a3b; --gold: #d8b45e; --gold-soft: #2a2516; --warn: #e39a66; --warn-soft: #2e2118;
  --ok: #6cc08e; --ok-soft: #17291f; --lu: #6cc08e; --quan: #8ea6ec; --ke: #d8b45e; --ji: #ec8585; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #11141c; --surface: #181c27; --ink: #e3e6ee; --muted: #a3a9ba; --faint: #767d90; --line: #2a3040;
  --accent: #8db5de; --accent-soft: #1d2a3b; --gold: #d8b45e; --gold-soft: #2a2516; --warn: #e39a66; --warn-soft: #2e2118;
  --ok: #6cc08e; --ok-soft: #17291f; --lu: #6cc08e; --quan: #8ea6ec; --ke: #d8b45e; --ji: #ec8585; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 16.5px; line-height: 1.85;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 0 56px; }
a { color: var(--accent); }
h1, h2, h3 { font-family: var(--font-display); letter-spacing: .04em; text-wrap: balance; }
h2 { font-size: 25px; line-height: 1.3; margin: 0; } h3 { font-size: 18.5px; margin: 8px 0 0; } p { margin: 0; }
.eyebrow { font-size: 13px; letter-spacing: .12em; color: var(--accent); font-weight: 500; }
.top { max-width: 1120px; margin: 0 auto; padding-block: 28px 16px; display: grid; gap: 10px; }
.top h1 { font-size: clamp(26px, 5.2vw, 40px); line-height: 1.25; margin: 0; }
.facts { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 0; padding: 0; list-style: none; }
.facts li { font-size: 13.5px; line-height: 1.4; padding: 5px 10px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); color: var(--muted); }
.facts b { color: var(--ink); font-weight: 500; }
.layout { max-width: 1120px; margin: 0 auto; display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 36px; align-items: start; }
.side { position: sticky; top: 16px; display: grid; gap: 2px; }
.side a { display: block; text-decoration: none; padding: 6px 12px; border-radius: 8px; font-size: 15px; color: var(--muted); line-height: 1.4; }
.side a:hover { background: var(--accent-soft); color: var(--ink); }
main { min-width: 0; display: grid; gap: 52px; }
section { scroll-margin-top: 72px; display: grid; gap: 16px; min-width: 0; }
.prose { max-width: var(--measure); display: grid; gap: 12px; }
.lead { color: var(--muted); max-width: var(--measure); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; display: grid; gap: 6px; align-content: start; }
.card h3 { margin: 0; font-size: 17px; display: flex; justify-content: space-between; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.card p { font-size: 15.5px; line-height: 1.75; }
.pill { font-family: var(--font-body); font-size: 12px; font-weight: 500; padding: 1px 8px; border-radius: 999px; white-space: nowrap; }
.pill.ok { background: var(--ok-soft); color: var(--ok); } .pill.mid { background: var(--gold-soft); color: var(--gold); }
.pill.ver { background: var(--accent-soft); color: var(--accent); } .pill.warn { background: var(--warn-soft); color: var(--warn); }
.tbl { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 14.5px; line-height: 1.7; }
th, td { text-align: left; vertical-align: top; padding: 9px 12px; border-bottom: 1px solid var(--line); }
tr:last-child td { border-bottom: 0; }
th { font-weight: 500; color: var(--muted); font-size: 13px; background: var(--bg); white-space: nowrap; }
td.k { white-space: nowrap; font-weight: 500; } tr.cur td { background: var(--gold-soft); }
.st-ok { color: var(--ok); font-weight: 500; } .st-warn { color: var(--gold); font-weight: 500; } .st-fail { color: var(--ji); font-weight: 700; }
.st-ok, .st-warn, .st-fail { white-space: nowrap; }
.pillars td, .pillars th { text-align: center; white-space: nowrap; }
.pillars .gz { font-family: var(--font-display); font-size: 24px; font-weight: 700; line-height: 1.3; }
.note { background: var(--warn-soft); border-radius: 12px; padding: 12px 16px; display: grid; gap: 8px; max-width: var(--measure); }
.note.info { background: var(--accent-soft); } .note h3 { margin: 0; font-size: 16px; color: var(--warn); } .note.info h3 { color: var(--accent); }
.note ul, .prose ul { margin: 0; padding-left: 1.2em; display: grid; gap: 6px; }
.bars { display: grid; gap: 8px; max-width: 32em; }
.bar { display: grid; grid-template-columns: 2.4em minmax(0, 1fr) 3.2em; align-items: center; gap: 10px; font-size: 14.5px; }
.bar .track { height: 12px; background: var(--bg); border-radius: 999px; border: 1px solid var(--line); overflow: hidden; display: block; }
.bar .fill { display: block; height: 100%; background: var(--accent); border-radius: 999px; } .bar .fill.self { background: var(--gold); }
.bar .v { font-variant-numeric: tabular-nums; color: var(--muted); text-align: right; }
.pan-wrap { overflow-x: auto; }
.pan { display: grid; min-width: 560px; max-width: 760px; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px;
  grid-template-areas: "p5 p6 p7 p8" "p4 ctr ctr p9" "p3 ctr ctr p10" "p2 p1 p0 p11"; }
.pc { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 8px 8px 6px; display: grid; gap: 4px; align-content: space-between; min-height: 118px; font-size: 13px; line-height: 1.45; }
.pc.ming { border: 2px solid var(--accent); } .pc.shen { outline: 1.5px dashed var(--gold); outline-offset: -5px; } .pc.now { background: var(--gold-soft); }
.pmaj { display: flex; flex-wrap: wrap; gap: 2px 8px; }
.ms { font-family: var(--font-display); font-weight: 700; font-size: 16px; display: inline-flex; align-items: baseline; gap: 2px; }
.ms small { font-family: var(--font-body); font-weight: 400; font-size: 11px; color: var(--faint); } .ms.empty { color: var(--faint); font-weight: 500; font-size: 14px; }
.pmin { display: flex; flex-wrap: wrap; gap: 0 6px; font-size: 12.5px; } .pmin .g { color: var(--accent); } .pmin .b { color: var(--warn); }
.zh { font-size: 11.5px; color: var(--muted); }
.pfoot { display: flex; justify-content: space-between; align-items: baseline; gap: 4px; border-top: 1px solid var(--line); padding-top: 4px; }
.pn { font-weight: 700; font-size: 13px; display: inline-flex; gap: 3px; align-items: center; }
.flag { font-size: 10.5px; font-weight: 500; padding: 0 4px; border-radius: 4px; background: var(--accent-soft); color: var(--accent); }
.pg, .pd { color: var(--faint); font-size: 11.5px; font-variant-numeric: tabular-nums; }
.pcenter { border: 1px dashed var(--line); border-radius: 8px; display: grid; align-content: center; justify-items: center; gap: 6px; padding: 12px; text-align: center; font-size: 13.5px; color: var(--muted); }
.cbig { font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--ink); } .cnote { font-size: 12px; color: var(--faint); }
.hua { display: inline-grid; place-items: center; min-width: 1.45em; height: 1.45em; border-radius: 4px; font-size: 11px; font-weight: 700; color: var(--surface); line-height: 1; margin-left: 2px; padding: 0 2px; vertical-align: 1px; font-family: var(--font-body); }
.hua.lu { background: var(--lu); } .hua.quan { background: var(--quan); } .hua.ke { background: var(--ke); } .hua.ji { background: var(--ji); }
.checklist { display: grid; gap: 8px; max-width: var(--measure); }
.chkitem { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 10px; align-items: start; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; cursor: pointer; }
.chkitem input { width: 18px; height: 18px; margin-top: 5px; accent-color: var(--accent); }
.chkitem small { display: block; color: var(--faint); font-size: 13px; line-height: 1.6; }
.chkitem:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
.tally { font-weight: 500; color: var(--accent); } .foot { color: var(--muted); font-size: 14px; line-height: 1.8; }
@media (max-width: 860px) {
  .layout { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .side { top: 0; z-index: 5; display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; background: var(--bg); padding-block: 10px;
    margin-inline: calc(-1 * max(16px, env(safe-area-inset-left, 0px))) calc(-1 * max(16px, env(safe-area-inset-right, 0px)));
    padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); border-bottom: 1px solid var(--line); }
  .side::-webkit-scrollbar { display: none; }
  .side a { flex: none; border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px; font-size: 14px; background: var(--surface); }
  main { gap: 44px; } h2 { font-size: 22px; }
}
'''

SCRIPT = r'''
(function () {
  var KEY = 'zwbz-check-' + (document.body.getAttribute('data-key') || '');
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.checklist input[type=checkbox]'));
  var tally = document.getElementById('tally');
  if (!tally || !boxes.length) return;
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { saved = {}; }
  function update() {
    var n = boxes.filter(function (b) { return b.checked; }).length, t = boxes.length;
    tally.textContent = '已勾选 ' + n + ' / ' + t + (n >= t * 0.7 ? '：和这张盘很贴合' : n >= t * 0.4 ? '：大体贴合' : '');
  }
  boxes.forEach(function (b) {
    if (saved[b.id]) b.checked = true;
    b.addEventListener('change', function () { saved[b.id] = b.checked; try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} update(); });
  });
  update();
})();
'''


def _hua(k):
    return f'<span class="hua {HUA_CLS[k]}">{E(k)}</span>' if k in HUA_CLS else ''


def _pill(label):
    return f'<span class="pill {AGREE_CLS.get(label, "mid")}">{E(label)}</span>' if label else ''


def _paras(text):
    if not text:
        return ''
    return ''.join(f'<p>{E(t)}</p>' for t in str(text).split('\n') if t.strip())


def _table(headers, rows, cls=''):
    h = ''.join(f'<th>{E(x)}</th>' for x in headers)
    body = ''.join(rows)
    return f'<div class="tbl"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


def _grid(zw, now_age):
    cells = []
    zihua = {(z['palace']): z for z in zw['zihua']}
    for p in zw['palaces']:
        b = BR.index(p['branch'])
        maj = ''.join(f'<span class="ms">{E(s["name"])}<small>{E(s.get("brightness", ""))}</small>{_hua(s.get("hua"))}</span>'
                      for s in p['stars'] if s['type'] == 'major') or '<span class="ms empty">空宫</span>'
        names = {s['name']: s for s in p['stars']}
        minor = ''.join(f'<span class="g">{E(n)}{_hua(names[n].get("hua"))}</span>' for n in GOOD if n in names)
        minor += ''.join(f'<span class="b">{E(n)}</span>' for n in BAD if n in names)
        cls = ['pc'] + (['ming'] if p['is_ming'] else []) + (['shen'] if p['is_shen'] else []) + \
              (['now'] if now_age and p['daxian'][0] <= now_age <= p['daxian'][1] else [])
        flags = ('<span class="flag">命</span>' if p['is_ming'] else '') + ('<span class="flag">身</span>' if p['is_shen'] else '')
        zh = ''.join(f'<span class="zh">{E(z["star"])}自化{E(z["hua"])}</span>' for z in zw['zihua'] if z['palace'] == p['name'])
        cells.append(f'<div class="{" ".join(cls)}" style="grid-area:p{b}"><div class="pmaj">{maj}</div><div class="pmin">{minor}</div>{zh}'
                     f'<div class="pfoot"><span class="pn">{E(p["name"])}{flags}</span><span class="pg">{E(p["stem"] + p["branch"])}</span>'
                     f'<span class="pd">{p["daxian"][0]}–{p["daxian"][1]}</span></div></div>')
    sh = ' '.join(f'{_hua(k)}{E(s)}' for k, s in zw['sihua'].items())
    center = (f'<div class="pcenter" style="grid-area:ctr"><p class="cbig">{E(zw["yin_yang_gender"])} · {E(zw["ju_name"])}</p>'
              f'<p>命主 {E(zw["mingzhu"])} · 身主 {E(zw["shenzhu"])}</p><p>生年四化 {sh}</p>'
              '<p class="cnote">外框加粗为命宫，虚线框为身宫，底色为当前大限</p></div>')
    return f'<div class="pan-wrap"><div class="pan">{"".join(cells)}{center}</div></div>'


def render(facts: dict, nar: dict) -> str:
    i, bz, zw = facts['input'], facts['bazi'], facts.get('ziwei')
    nar = nar or {}
    yrs = facts.get('years') or []
    now_age = yrs[0]['age_xu'] if yrs else None
    cur_dy = yrs[0]['dayun'] if yrs else ''
    cur_dx = yrs[0]['ziwei']['daxian_palace'] if yrs and 'ziwei' in yrs[0] else ''
    g = '男' if i['gender'] == 'male' else '女'
    place = i.get('place')
    chips = [('公历', f"{i['solar_date']} {i['time_input'] if i['time_input'] not in (None, 'unknown') else ''}")]
    if i.get('true_solar'):
        chips.append((f"{place['city']}真太阳时", f"{i['basis_time'][11:]}" + (f" · {zw['hour_branch']}时" if zw else '')))
    elif zw:
        chips.append(('时辰', f"{zw['hour_branch']}时（钟表时间）"))
    chips += [('农历', facts['lunar']['text']), ('', g), ('八字', ' '.join(bz['pillars']))]
    if zw:
        chips.append(('紫微', f"{zw['yin_yang_gender']} {zw['ju_name']}"))
    if cur_dy or cur_dx:
        chips.append(('现行', f"{cur_dy}大运 · {cur_dx}大限" if cur_dx else f'{cur_dy}大运'))
    chips_html = ''.join(f'<li>{E(a)} <b>{E(b)}</b></li>' if a else f'<li><b>{E(b)}</b></li>' for a, b in chips)
    ming_major = ''.join(s['name'] for s in zw['palaces'][0]['stars'] if s['type'] == 'major') if zw else ''
    headline = nar.get('headline') or (f'{ming_major}坐命 · {bz["day_master"]}日主' if ming_major else f'命盘分析 · {bz["day_master"]}日主')
    title = nar.get('title') or headline.split('·')[0].strip()

    S = []  # sections
    nav = []

    def sec(sid, label, inner, lead=''):
        nav.append(f'<a href="#{sid}">{E(label)}</a>')
        S.append(f'<section id="{sid}" aria-labelledby="h-{sid}"><h2 id="h-{sid}">{E(label)}</h2>'
                 + (f'<p class="lead">{E(lead)}</p>' if lead else '') + inner + '</section>')

    # 结论
    cards = ''.join(f'<div class="card"><h3>{E(c.get("title"))} {_pill(c.get("agree"))}</h3><p>{E(c.get("text"))}</p></div>' for c in nar.get('summary', []))
    if cards:
        sec('summary', '结论速览', f'<div class="cards">{cards}</div>', '八字和紫微各自排盘、各自分析，两边说法一致的结论更值得参考。')

    # 核对
    st_txt = {'ok': ('st-ok', '✓ 一致'), 'warn': ('st-warn', '注意'), 'fail': ('st-fail', '✗ 不一致')}
    rows = [f'<tr><td class="k">{E(c["item"])}</td><td>{E(c["result"])}</td><td>{E(c["method"])}</td>'
            f'<td class="{st_txt[c["status"]][0]}">{st_txt[c["status"]][1]}</td></tr>' for c in facts['checks']]
    tbits = []
    if i.get('true_solar'):
        tbits.append(f"出生地 {place['province']}{place['city']}（东经 {place['longitude']}°），钟表 {i['clock'][11:]}，经度修正 {i['true_solar']['longitude_minutes']:+} 分，均时差 {i['true_solar']['eot_minutes']:+} 分，真太阳时 {i['basis_time'][11:]}")
    inner = _table(['项目', '结果', '怎么核对的', '结论'], rows)
    if tbits:
        inner = f'<div class="prose"><p>{E("；".join(tbits))}。</p></div>' + inner
    if facts['warnings']:
        inner += '<div class="note"><h3>需要确认</h3><ul>' + ''.join(f'<li>{E(w)}</li>' for w in facts['warnings']) + '</ul></div>'
    if facts['notes']:
        inner += '<div class="note info"><h3>口径说明</h3><ul>' + ''.join(f'<li>{E(n)}</li>' for n in facts['notes']) + '</ul></div>'
    sec('verify', '排盘核对', inner, '盘排错了，后面的分析都没有意义。下面每一项都用互相独立的方法算过。')

    # 八字
    nb = nar.get('bazi', {})
    det = bz['detail']
    head = '<tr><th></th>' + ''.join(f'<th>{E(d["pos"])}柱</th>' for d in det) + '</tr>'
    r1 = '<tr><th>十神</th>' + ''.join(f'<td>{E(d["stem_god"])}</td>' for d in det) + '</tr>'
    r2 = '<tr><th>干支</th>' + ''.join(f'<td class="gz">{E(d["pillar"][0])}<br>{E(d["pillar"][1])}</td>' for d in det) + '</tr>'
    r3 = '<tr><th>藏干</th>' + ''.join('<td>' + '<br>'.join(f'{E(h["stem"])} {E(h["god"])}' for h in d['hidden']) + '</td>' for d in det) + '</tr>'
    r4 = '<tr><th>日主在此</th>' + ''.join(f'<td>{E(d["stage"])}</td>' for d in det) + '</tr>'
    r5 = '<tr><th>纳音</th>' + ''.join(f'<td>{E(d["nayin"])}</td>' for d in det) + '</tr>'
    inner = f'<div class="tbl"><table class="pillars"><thead>{head}</thead><tbody>{r1}{r2}{r3}{r4}{r5}</tbody></table></div>'
    rel = '；'.join(bz['relations']) or '原局没有明显的合冲刑害'
    ss = '，'.join(f'{k}在{v}' for k, v in bz['shensha'].items() if v)
    inner += f'<div class="prose"><p>原局作用：{E(rel)}。日柱旬空在{E(bz["kongwang"]["日柱旬空"])}，年柱旬空在{E(bz["kongwang"]["年柱旬空"])}。神煞：{E(ss)}。</p></div>'
    s = bz.get('strength')
    if s:
        mx = max(s['score'].values()) or 1
        order = s['self_elements'] + [w for w in '木火土金水' if w not in s['self_elements']]
        score = s['score']
        bars = ''.join(f'<div class="bar"><span>{w}</span><span class="track"><span class="fill{" self" if w in s["self_elements"] else ""}" style="width:{score[w] / mx * 100:.1f}%"></span></span><span class="v">{score[w]}</span></div>' for w in order)
        aria = '五行计分 ' + '，'.join(f'{w} {score[w]}' for w in order)
        inner += f'<h3>旺衰：{E(nb.get("strength_label") or s["label"])}</h3><div class="bars" role="img" aria-label="{E(aria)}">{bars}</div>'
        inner += (f'<div class="prose"><p class="foot">计分：{E(s["method"])}。金色是生扶日主的五行，共 {s["self_vs_other"][0]}；蓝色是克泄耗日主的五行，共 {s["self_vs_other"][1]}'
                  f'（月令加权后 {s["self_vs_other_month_weighted"][0]} 对 {s["self_vs_other_month_weighted"][1]}）。{E(s["tiaohou"])}。</p></div>')
    inner += f'<div class="prose">{_paras(nb.get("strength"))}{_paras(nb.get("pattern"))}</div>'
    if nb.get('xiji'):
        inner += _table(['喜忌', '五行', '理由'], [f'<tr><td class="k">{E(x.get("level"))}</td><td>{E(x.get("wuxing"))}</td><td>{E(x.get("why"))}</td></tr>' for x in nb['xiji']])
    for key, label in (('personality', '性格'), ('career', '事业'), ('wealth', '财运'), ('health', '健康（传统五行对应）')):
        if nb.get(key):
            inner += f'<div class="prose"><p><b>{label}。</b>{E(nb[key])}</p></div>'
    if nb.get('relatives'):
        inner += _table(['六亲', '八字里的看法'], [f'<tr><td class="k">{E(x.get("who"))}</td><td>{E(x.get("text"))}</td></tr>' for x in nb['relatives']])
    dnotes = nb.get('dayun', {})
    cur = yrs[0]['dayun'] if yrs else ''
    rows = []
    for k, d in enumerate(bz['dayun'][:8]):
        nxt = bz['dayun'][k + 1]['start'][:7] if k + 1 < len(bz['dayun']) else ''
        rel = '；'.join(d.get('relations', [])) or '与原局无明显作用'
        rows.append(f'<tr class="{"cur" if d["pillar"] == cur else ""}"><td class="k">{E(d["pillar"])}{"（当前）" if d["pillar"] == cur else ""}</td>'
                    f'<td>{E(d["start"][:7])} 起，约 {d.get("start_age", d["start_age_xu"])} 岁</td><td>{E(d["stem_god"])} / {E(d["branch_god"])}</td>'
                    f'<td>{E(rel)}</td><td>{E(dnotes.get(d["pillar"], ""))}</td></tr>')
    inner += f'<h3>大运（{"顺" if bz["yun"]["forward"] else "逆"}排，约 {bz["yun"]["start_age"]} 岁起运）</h3>' + _table(['大运', '时间', '十神', '与原局', '要点'], rows)
    sec('bazi', '八字分析', inner)

    # 紫微
    if zw:
        nz = nar.get('ziwei', {})
        inner = _grid(zw, now_age)
        inner += f'<div class="prose">{"".join(f"<p><b>{lab}</b>{E(nz[k])}</p>" for k, lab in (("ming", "命宫。"), ("shen", "身宫。"), ("sanfang", "三方四正。")) if nz.get(k))}</div>'
        if nz.get('patterns'):
            inner += _table(['格局', '成立情况'], [f'<tr><td class="k">{E(x.get("name"))}</td><td>{E(x.get("status"))}</td></tr>' for x in nz['patterns']])
        if nz.get('palaces'):
            inner += _table(['宫位', '要点'], [f'<tr><td class="k">{E(x.get("palace"))}</td><td>{E(x.get("text"))}</td></tr>' for x in nz['palaces']])
        dxn = nz.get('daxian', {})
        rows = []
        birth = i['birth_year_for_age']
        for r in daxian_rows(zw)[:7]:
            a, b = r['range']
            key = f'{a}-{b}'
            is_cur = now_age and a <= now_age <= b
            sh = '，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in r['sihua'])
            rows.append(f'<tr class="{"cur" if is_cur else ""}"><td class="k">{a}–{b}</td><td>{birth + a - 1}–{birth + b - 1}</td><td>{E(r["palace"])}（{E(r["gz"])}）</td><td>{E(sh)}</td><td>{E(dxn.get(key, ""))}</td></tr>')
        inner += '<h3>大限</h3>' + _table(['虚岁', '年份', '大限宫', '宫干四化', '要点'], rows)
        sec('ziwei', '紫微斗数分析', inner)

    if nar.get('cross'):
        rows = [f'<tr><td class="k">{E(x.get("topic"))}</td><td>{E(x.get("bazi"))}</td><td>{E(x.get("ziwei"))}</td><td>{_pill(x.get("agree"))}</td></tr>' for x in nar['cross']]
        sec('cross', '交叉印证', _table(['主题', '八字', '紫微', '一致度'], rows), '两套体系的算法完全不同：八字看干支五行，紫微看星曜宫位。说法一致的地方更可靠。')

    if yrs:
        ytips = nar.get('years', {})
        rows = []
        for k, r in enumerate(yrs):
            z = r.get('ziwei')
            zt = (f"流年命宫在{z['ming_palace']}，大限{z['daxian_palace']}，小限{z['xiaoxian_palace']}；" + '，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in z['sihua'])) if z else ''
            rows.append(f'<tr class="{"cur" if k == 0 else ""}"><td class="k">{r["year"]} {E(r["gz"])}<br>虚岁 {r["age_xu"]}</td>'
                        f'<td>{E(r["gods"])}；{E("；".join(r["bazi_relations"]) or "与原局无明显作用")}</td><td>{E(zt)}</td><td>{E(ytips.get(str(r["year"]), ""))}</td></tr>')
        sec('years', f'{yrs[0]["year"]}–{yrs[-1]["year"]} 逐年看', _table(['年份', '八字', '紫微', '提示'], rows),
            '八字一栏是流年与原局、大运的作用；紫微一栏是流年命宫的位置和流年四化落在哪一宫。')

    mo = facts.get('months')
    if mo:
        rows = [f'<tr><td class="k">{E(r["pillar"])}</td><td>{E(r["jie"])} {E(r["start"][5:10])}–{E(r["end"][5:10])}</td><td>{E(r["gods"])}</td>'
                f'<td>{E("；".join(r["relations"]) or "与原局无明显作用")}</td></tr>' for r in mo['bazi']]
        inner = '<h3>八字流月（按节气换月）</h3>' + _table(['月柱', '时间', '十神', '与原局、大运、流年'], rows)
        if mo.get('ziwei'):
            rows = [f'<tr><td class="k">{E(r["label"])}</td><td>{E(r["start"][5:])}–{E(r["end"][5:])}</td><td>{E(r["gz"])}</td>'
                    f'<td>流月命宫在{E(r["palace"])}；' + E('，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in r['sihua'])) + '</td></tr>' for r in mo['ziwei']]
            inner += '<h3>紫微流月（按农历月，流年斗君起正月）</h3>' + _table(['农历月', '公历日期', '干支', '流月命宫与四化'], rows)
        tips = nar.get('months') or []
        if tips:
            inner += '<div class="prose">' + ''.join(f'<p><b>{E(x.get("label"))}：</b>{E(x.get("text"))}</p>' for x in tips) + '</div>'
        sec('months', f'{mo["year"]} 年流月', inner, '八字流月按节气换月，紫微流月按农历月，两者的月份边界不同。')

    if nar.get('checklist'):
        items = ''.join(f'<label class="chkitem"><input type="checkbox" id="c{k}"><span>{E(x.get("text"))}<small>{E(x.get("basis"))}</small></span></label>'
                        for k, x in enumerate(nar['checklist'], 1))
        sec('check', '回溯核对', f'<p class="tally" id="tally" aria-live="polite"></p><div class="checklist">{items}</div>',
            '下面每一条都是这张盘对过去的推断，照自己的经历勾选。对上的越多，说明出生时间和这张盘越贴合；大多数对不上，就不要太把后面的推断当真。勾选只保存在你自己的浏览器里。')

    ds = facts.get('dataset')
    if ds and ds.get('dims'):
        rows = [f'<tr><td class="k">{E(d["label"])}</td><td>{E(d["tone"])}</td></tr>' for d in ds['dims']]
        sec('dataset', '数据集 13 维速览', _table(['维度', '一句话定调'], rows),
            f'{ATTRIBUTION}。这是第三方现成解读，按时辰直接排盘、亮度用旧表，和上面分析冲突时以上面为准。')

    if nar.get('advice'):
        sec('advice', '建议', '<div class="prose">' + ''.join(f'<p><b>{E(a.get("title"))}：</b>{E(a.get("text"))}</p>' for a in nar['advice']) + '</div>')

    notes = ['<p><b>核对方法。</b>节气和朔日用 PyEphem 天文算法计算；八字和农历另用 lunar-javascript 核对；紫微盘用按安星诀独立实现的程序与 iztro 逐项比对；主星亮度用《紫微斗数全书》表。</p>',
             '<p><b>流派。</b>八字以扶抑和调候为主；紫微以三合派星曜和生年四化为主，宫干自化和化入作参考。不同流派对旺衰、亮度、飞化的看法会有出入。</p>',
             '<p><b>局限。</b>命理是传统文化里的一套解释体系，没有科学证据表明它能预测具体事件。本报告是按传统规则推演的结果，可以当作认识自己、做规划时的参考，不能替代医疗、法律、财务和婚恋方面的专业判断。</p>']
    if ds and ds.get('dims'):
        notes.append(f'<p><b>数据来源。</b>{E(ATTRIBUTION)}（CC BY 4.0）。数据集正文引用的倪海厦原话仅限非商业的学习研究。</p>')
    sec('notes', '说明', '<div class="prose foot">' + ''.join(notes) + '</div>')

    return ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{E(title)}</title>\n<style>{CSS}</style>\n</head>\n<body data-key="{E(facts.get("dataset_key", ""))}">\n'
            f'<header class="top"><p class="eyebrow">命格综合分析 · 八字 × 紫微斗数</p><h1>{E(headline)}</h1><ul class="facts">{chips_html}</ul></header>\n'
            f'<div class="layout"><nav class="side" aria-label="章节">{"".join(nav)}</nav><main>{"".join(S)}</main></div>\n'
            f'<script>{SCRIPT}</script>\n</body>\n</html>\n')


def _md_cell(s) -> str:
    return str(s if s is not None else '').replace('|', '｜').replace('\n', ' ')


def _md_table(headers, rows) -> str:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
    out += ['| ' + ' | '.join(_md_cell(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def render_md(facts: dict, nar: dict) -> str:
    """Markdown 版完整报告：给发不了 HTML 附件的场合，或者直接贴在聊天里。"""
    i, bz, zw = facts['input'], facts['bazi'], facts.get('ziwei')
    nar = nar or {}
    yrs = facts.get('years') or []
    L = [f"# {nar.get('headline') or '命格分析'}", '', '> 命格综合分析 · 八字 × 紫微斗数', '']
    g = '男' if i['gender'] == 'male' else '女'
    basis = f"{i['basis']} {i['basis_time'][11:]}" if i.get('basis_time') else '无时辰'
    L.append(f"- 公历 {i['solar_date']} {i['time_input'] or ''}，{g}，{(i['place'] or {}).get('city', '出生地未提供')}；排盘基准：{basis}")
    L.append(f"- 农历 {facts['lunar']['text']}；八字 {' '.join(bz['pillars'])}" + (f"；紫微 {zw['yin_yang_gender']} {zw['ju_name']}" if zw else ''))
    L.append('')
    if nar.get('summary'):
        L += ['## 结论速览', ''] + [f"- **{c.get('title')}**（{c.get('agree', '')}）：{c.get('text')}" for c in nar['summary']] + ['']
    L += ['## 排盘核对', '', _md_table(['项目', '结果', '结论'], [[c['item'], c['result'], {'ok': '✓ 一致', 'warn': '注意', 'fail': '✗ 不一致'}[c['status']]] for c in facts['checks']]), '']
    if facts.get('warnings'):
        L += ['**需要确认：**'] + [f'- {w}' for w in facts['warnings']] + ['']
    if facts.get('notes'):
        L += ['**口径说明：**'] + [f'- {n}' for n in facts['notes']] + ['']
    nb = nar.get('bazi', {})
    L += ['## 八字分析', '', _md_table([''] + [f"{d['pos']}柱" for d in bz['detail']],
          [['十神'] + [d['stem_god'] for d in bz['detail']], ['干支'] + [d['pillar'] for d in bz['detail']],
           ['藏干'] + ['、'.join(h['stem'] + h['god'] for h in d['hidden']) for d in bz['detail']],
           ['日主在此'] + [d['stage'] for d in bz['detail']], ['纳音'] + [d['nayin'] for d in bz['detail']]]), '']
    L.append('原局作用：' + ('；'.join(bz['relations']) or '没有明显的合冲刑害') + '。')
    s = bz.get('strength')
    if s:
        L.append(f"旺衰：**{nb.get('strength_label') or s['label']}**（五行计分 " + '，'.join(f'{w}{v}' for w, v in s['score'].items()) + f"；生扶 {s['self_vs_other'][0]} 对克泄耗 {s['self_vs_other'][1]}；{s['tiaohou']}）")
    L.append('')
    for k, lab in (('strength', ''), ('pattern', ''), ('personality', '性格'), ('career', '事业'), ('wealth', '财运'), ('health', '健康（传统五行对应）')):
        if nb.get(k):
            L += [(f'**{lab}：**' if lab else '') + nb[k], '']
    if nb.get('xiji'):
        L += [_md_table(['喜忌', '五行', '理由'], [[x.get('level'), x.get('wuxing'), x.get('why')] for x in nb['xiji']]), '']
    if nb.get('relatives'):
        L += [_md_table(['六亲', '看法'], [[x.get('who'), x.get('text')] for x in nb['relatives']]), '']
    dn = nb.get('dayun', {})
    L += ['### 大运', '', _md_table(['大运', '起运', '十神', '与原局', '要点'],
          [[d['pillar'], f"{d['start'][:7]}（约 {d.get('start_age', '')} 岁）", f"{d['stem_god']}/{d['branch_god']}", '；'.join(d.get('relations', [])), dn.get(d['pillar'], '')] for d in bz['dayun'][:8]]), '']
    if zw:
        nz = nar.get('ziwei', {})
        rows = []
        for p in zw['palaces']:
            mj = '、'.join(f"{x['name']}({x['brightness']})" + (f"化{x['hua']}" if 'hua' in x else '') for x in p['stars'] if x['type'] == 'major') or '空宫'
            mn = '、'.join(x['name'] + (f"化{x['hua']}" if 'hua' in x else '') for x in p['stars'] if x['type'] == 'minor')
            rows.append([p['name'] + ('（命）' if p['is_ming'] else '') + ('（身）' if p['is_shen'] else ''), p['stem'] + p['branch'], mj, mn, f"{p['daxian'][0]}–{p['daxian'][1]}"])
        L += ['## 紫微斗数分析', '', _md_table(['宫位', '干支', '主星', '六吉六煞禄马', '大限'], rows), '']
        for k, lab in (('ming', '命宫'), ('shen', '身宫'), ('sanfang', '三方四正')):
            if nz.get(k):
                L += [f'**{lab}：**' + nz[k], '']
        if nz.get('patterns'):
            L += [_md_table(['格局', '成立情况'], [[x.get('name'), x.get('status')] for x in nz['patterns']]), '']
        if nz.get('palaces'):
            L += [_md_table(['宫位', '要点'], [[x.get('palace'), x.get('text')] for x in nz['palaces']]), '']
        dxn = nz.get('daxian', {})
        L += ['### 大限', '', _md_table(['虚岁', '大限宫', '宫干四化', '要点'],
              [[f"{r['range'][0]}–{r['range'][1]}", f"{r['palace']}（{r['gz']}）", '，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in r['sihua']),
                dxn.get(f"{r['range'][0]}-{r['range'][1]}", '')] for r in daxian_rows(zw)[:7]]), '']
    if nar.get('cross'):
        L += ['## 交叉印证', '', _md_table(['主题', '八字', '紫微', '一致度'], [[x.get('topic'), x.get('bazi'), x.get('ziwei'), x.get('agree')] for x in nar['cross']]), '']
    if yrs:
        yt = nar.get('years', {})
        L += [f"## {yrs[0]['year']}–{yrs[-1]['year']} 逐年看", '', _md_table(['年份', '八字', '紫微', '提示'],
              [[f"{r['year']} {r['gz']}（虚岁 {r['age_xu']}）", f"{r['gods']}；" + ('；'.join(r['bazi_relations']) or '与原局无明显作用'),
                (f"流年命宫在{r['ziwei']['ming_palace']}，大限{r['ziwei']['daxian_palace']}；" + '，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in r['ziwei']['sihua'])) if 'ziwei' in r else '',
                yt.get(str(r['year']), '')] for r in yrs]), '']
    mo = facts.get('months')
    if mo:
        L += [f"## {mo['year']} 年流月", '', _md_table(['八字月柱', '时间', '十神', '作用'], [[r['pillar'], f"{r['jie']} {r['start'][5:10]}–{r['end'][5:10]}", r['gods'], '；'.join(r['relations'])] for r in mo['bazi']]), '']
        if mo.get('ziwei'):
            L += [_md_table(['农历月', '公历日期', '干支', '流月命宫与四化'], [[r['label'], f"{r['start'][5:]}–{r['end'][5:]}", r['gz'], f"流月命宫在{r['palace']}；" + '，'.join(f"{x['star']}{x['hua']}入{x['palace']}" for x in r['sihua'])] for r in mo['ziwei']]), '']
        L += [f"- **{x.get('label')}**：{x.get('text')}" for x in (nar.get('months') or [])] + ['']
    if nar.get('checklist'):
        L += ['## 回溯核对', '', '照自己的经历勾选，对上的越多，说明出生时间和这张盘越贴合。', ''] + [f"- [ ] {x.get('text')}（依据：{x.get('basis')}）" for x in nar['checklist']] + ['']
    ds = facts.get('dataset')
    if ds and ds.get('dims'):
        L += ['## 数据集 13 维速览', '', _md_table(['维度', '一句话定调'], [[d['label'], d['tone']] for d in ds['dims']]), '', f'> {ATTRIBUTION}（CC BY 4.0）。', '']
    if nar.get('advice'):
        L += ['## 建议', ''] + [f"- **{a.get('title')}**：{a.get('text')}" for a in nar['advice']] + ['']
    L += ['## 说明', '', '命理是传统文化里的一套解释体系，没有科学证据表明它能预测具体事件。本报告按传统规则推演，仅供参考，不能替代医疗、法律、财务和婚恋方面的专业判断。', '']
    return '\n'.join(L)


def render_chat(facts: dict, nar: dict) -> str:
    """聊天里直接发的短摘要。"""
    i, bz, zw = facts['input'], facts['bazi'], facts.get('ziwei')
    nar = nar or {}
    L = [nar.get('headline') or '命格分析']
    basis = f"{i['basis']} {i['basis_time'][11:]}" + (f"（{zw['hour_branch']}时）" if zw else '') if i.get('basis_time') else '无时辰'
    L.append(f"排盘：公历 {i['solar_date']}，{basis}；八字 {' '.join(bz['pillars'])}" + (f"；紫微 {zw['ju_name']}，命宫{zw['palaces'][0]['stem']}{zw['ming_branch']}" if zw else ''))
    fails = [c for c in facts['checks'] if c['status'] == 'fail']
    L.append('核对：' + ('全部通过（天文算法、lunar-javascript、iztro 三方一致）' if not fails else f'有 {len(fails)} 项不一致，报告暂停'))
    if facts.get('warnings'):
        L.append('需要确认：' + '；'.join(facts['warnings']))
    for c in nar.get('summary', [])[:6]:
        L.append(f"· {c.get('title')}：{c.get('text')}")
    yrs = facts.get('years') or []
    if yrs and (nar.get('years') or {}).get(str(yrs[0]['year'])):
        L.append(f"· {yrs[0]['year']} 年：{nar['years'][str(yrs[0]['year'])]}")
    L.append('完整报告见附件。命理是传统文化的解释体系，仅供参考。')
    return '\n'.join(L)


def render_files(facts_path: str, narrative_path: str, out_path: str, fmt: str = 'html'):
    facts = json.load(open(facts_path, encoding='utf-8'))
    nar = json.load(open(narrative_path, encoding='utf-8')) if narrative_path else {}
    text = {'html': render, 'md': render_md, 'chat': render_chat}[fmt](facts, nar)
    open(out_path, 'w', encoding='utf-8').write(text)
    return text
