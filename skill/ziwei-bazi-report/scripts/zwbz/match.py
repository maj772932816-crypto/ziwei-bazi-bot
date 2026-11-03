"""合盘：两个人的八字与紫微对照（感情、合伙都可用）。

只整理客观的对照事实：日干、日支（配偶宫）、年支（生肖）的合冲刑害，五行能否互补，命宫关系，
双方生年四化落入对方命盘的哪一宫。好坏的判断交给解读，并要求两边说法都写清依据。
"""
import html
import json

from . import bazi
from .report import CSS, _md_table, _paras, _pill, _table
from .ziwei import SIHUA, palace_of

E = lambda s: html.escape(str(s if s is not None else ''), quote=True)  # noqa: E731
ST, BR, WX = bazi.STEMS, bazi.BRANCHES, bazi.WX
FOCUS = ['命宫', '夫妻', '福德', '财帛', '官禄', '迁移', '子女', '田宅']


def _xi(f: dict) -> list:
    """按程序的旺衰参考标签和季节，粗略给出喜用五行（只作对照用）。"""
    s = f['bazi'].get('strength')
    if not s:
        return []
    self_wx = s['self_elements']
    other = [w for w in WX if w not in self_wx]
    xi = list(self_wx) if '弱' in s['label'] else other
    if s['season'] == '冬' and '火' not in xi:
        xi.insert(0, '火')
    if s['season'] == '夏' and '水' not in xi:
        xi.insert(0, '水')
    return xi


def _strong(f: dict) -> list:
    s = f['bazi'].get('strength')
    if not s:
        return []
    return [w for w, _ in sorted(s['score'].items(), key=lambda kv: -kv[1])[:2]]


def _rel(a_label, a, b_label, b, stems=False) -> list:
    if stems:
        return bazi.relations({a_label: a, b_label: b}, {})
    return bazi.relations({}, {a_label: a, b_label: b})


def _sheng_ke(a: str, b: str) -> str:
    ea, eb = bazi.STEM_WX[ST.index(a)], bazi.STEM_WX[ST.index(b)]
    if ea == eb:
        return '同五行'
    if (ea + 1) % 5 == eb:
        return f'{a}生{b}'
    if (eb + 1) % 5 == ea:
        return f'{b}生{a}'
    if (ea + 2) % 5 == eb:
        return f'{a}克{b}'
    return f'{b}克{a}'


def _person(f: dict, tag: str) -> dict:
    i, bz, zw = f['input'], f['bazi'], f.get('ziwei')
    return {
        'tag': tag, 'name': i.get('name') or tag, 'gender': '男' if i['gender'] == 'male' else '女',
        'solar': f"{i['solar_date']} {i['time_input'] or ''}", 'lunar': f['lunar']['text'], 'pillars': bz['pillars'],
        'day_master': bz['day_master'], 'zodiac': f['lunar']['text'][1],
        'strength': (bz.get('strength') or {}).get('label', ''), 'xi': _xi(f), 'strong': _strong(f),
        'ming': (zw['palaces'][0]['stem'] + zw['ming_branch'] + ' ' + ('、'.join(s['name'] for s in zw['palaces'][0]['stars'] if s['type'] == 'major') or '空宫')) if zw else '',
        'spouse_palace': next(('、'.join(s['name'] for s in p['stars'] if s['type'] == 'major') or '空宫') for p in zw['palaces'] if p['name'] == '夫妻') if zw else '',
        'ju': zw['ju_name'] if zw else '',
    }


def match(fa: dict, fb: dict) -> dict:
    A, B = _person(fa, '甲方'), _person(fb, '乙方')
    da, db = fa['bazi']['day_master'], fb['bazi']['day_master']
    out = {'tool': 'zwbz-match', 'a': A, 'b': B, 'bazi': {}, 'ziwei': {}}
    bz = out['bazi']
    bz['day_stems'] = {'pair': da + db, 'relation': _rel('甲方日', da, '乙方日', db, stems=True) or ['无合冲'],
                       'sheng_ke': _sheng_ke(da, db),
                       'a_sees_b': bazi.ten_god(da, db), 'b_sees_a': bazi.ten_god(db, da)}
    bz['day_branches'] = {'pair': fa['bazi']['pillars'][2][1] + fb['bazi']['pillars'][2][1],
                          'relation': _rel('甲方日支', fa['bazi']['pillars'][2][1], '乙方日支', fb['bazi']['pillars'][2][1]) or ['无合冲刑害']}
    bz['year_branches'] = {'pair': fa['bazi']['pillars'][0][1] + fb['bazi']['pillars'][0][1],
                           'relation': _rel('甲方年支', fa['bazi']['pillars'][0][1], '乙方年支', fb['bazi']['pillars'][0][1]) or ['无合冲刑害']}
    star = {'male': ('正财', '偏财'), 'female': ('正官', '七杀')}
    bz['spouse_star'] = {
        'a': f"乙方日干{db}是甲方的{bazi.ten_god(da, db)}" + ('（正是甲方的夫妻星）' if bazi.ten_god(da, db) in star[fa['input']['gender']] else ''),
        'b': f"甲方日干{da}是乙方的{bazi.ten_god(db, da)}" + ('（正是乙方的夫妻星）' if bazi.ten_god(db, da) in star[fb['input']['gender']] else ''),
    }
    bz['wuxing'] = {
        'a_xi': A['xi'], 'b_strong': B['strong'], 'a_gets': sorted(set(A['xi']) & set(B['strong'])),
        'b_xi': B['xi'], 'a_strong': A['strong'], 'b_gets': sorted(set(B['xi']) & set(A['strong'])),
        'method': '喜用按各自的旺衰参考标签和季节粗略推定；对方原局五行计分最高的两项算「对方带来的五行」',
    }
    za, zb = fa.get('ziwei'), fb.get('ziwei')
    if za and zb:
        zw = out['ziwei']
        zw['ming_branches'] = {'pair': za['ming_branch'] + zb['ming_branch'],
                               'relation': _rel('甲方命宫', za['ming_branch'], '乙方命宫', zb['ming_branch']) or ['无合冲刑害']}

        def fly(src, dst):
            res = []
            for k, s in dict(zip('禄权科忌', SIHUA[src['year_gz'][0]].split())).items():
                pl = palace_of(dst, s)
                res.append({'hua': k, 'star': s, 'palace': pl, 'focus': pl in FOCUS})
            return res
        zw['a_to_b'] = fly(za, zb)
        zw['b_to_a'] = fly(zb, za)
        zw['a_ming_vs_b_spouse'] = {'a_ming': A['ming'], 'b_spouse': B['spouse_palace']}
        zw['b_ming_vs_a_spouse'] = {'b_ming': B['ming'], 'a_spouse': A['spouse_palace']}
        zw['method'] = '甲方生年四化（按甲方年干）落在乙方命盘的哪一宫，反之亦然；化禄、化权入对方命、夫妻、福德等宫较受重视，化忌入这些宫提示要多磨合'
    return out


def brief(m: dict) -> str:
    A, B, bz, zw = m['a'], m['b'], m['bazi'], m.get('ziwei') or {}
    L = ['【双方】']
    for p in (A, B):
        who = f"{p['name']}，" if p['name'] != p['tag'] else ''
        L.append(f"  {p['tag']}（{who}{p['gender']}）：公历 {p['solar']}；农历 {p['lunar']}；八字 {' '.join(p['pillars'])}；日主{p['day_master']}，"
                 f"旺衰参考{p['strength']}，喜用（粗略）{''.join(p['xi'])}，原局最旺{''.join(p['strong'])}" + (f"；紫微 {p['ju']}，命宫 {p['ming']}，夫妻宫 {p['spouse_palace']}" if p['ming'] else ''))
    L.append('【八字对照】')
    L.append(f"  日干 {bz['day_stems']['pair']}：{'；'.join(bz['day_stems']['relation'])}；{bz['day_stems']['sheng_ke']}；甲方看乙方是{bz['day_stems']['a_sees_b']}，乙方看甲方是{bz['day_stems']['b_sees_a']}")
    L.append(f"  日支（配偶宫）{bz['day_branches']['pair']}：{'；'.join(bz['day_branches']['relation'])}")
    L.append(f"  年支（生肖）{bz['year_branches']['pair']}：{'；'.join(bz['year_branches']['relation'])}")
    L.append(f"  夫妻星：{bz['spouse_star']['a']}；{bz['spouse_star']['b']}")
    w = bz['wuxing']
    L.append(f"  五行互补：甲方喜{''.join(w['a_xi'])}，乙方最旺{''.join(w['b_strong'])} → 甲方得到{''.join(w['a_gets']) or '无'}；乙方喜{''.join(w['b_xi'])}，甲方最旺{''.join(w['a_strong'])} → 乙方得到{''.join(w['b_gets']) or '无'}（{w['method']}）")
    if zw:
        L.append('【紫微对照】')
        L.append(f"  命宫 {zw['ming_branches']['pair']}：{'；'.join(zw['ming_branches']['relation'])}")
        L.append('  甲方生年四化入乙方：' + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in zw['a_to_b']))
        L.append('  乙方生年四化入甲方：' + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in zw['b_to_a']))
        L.append(f"  甲方命宫 {zw['a_ming_vs_b_spouse']['a_ming']} 对 乙方夫妻宫 {zw['a_ming_vs_b_spouse']['b_spouse']}；乙方命宫 {zw['b_ming_vs_a_spouse']['b_ming']} 对 甲方夫妻宫 {zw['b_ming_vs_a_spouse']['a_spouse']}")
    return '\n'.join(L)


def render_html(m: dict, nar: dict) -> str:
    A, B, bz, zw = m['a'], m['b'], m['bazi'], m.get('ziwei') or {}
    nar = nar or {}
    rows = [f'<tr><td class="k">{E(p["tag"])}</td><td>{E(p["name"])}（{E(p["gender"])}）</td><td>{E(p["solar"])}</td><td>{E(" ".join(p["pillars"]))}</td>'
            f'<td>{E(p["ju"])} {E(p["ming"])}</td></tr>' for p in (A, B)]
    S = [f'<section id="people"><h2>双方</h2>{_table(["", "称呼", "公历", "八字", "紫微命宫"], rows)}</section>']
    if nar.get('summary'):
        cards = ''.join(f'<div class="card"><h3>{E(c.get("title"))} {_pill(c.get("agree"))}</h3><p>{E(c.get("text"))}</p></div>' for c in nar['summary'])
        S.append(f'<section id="summary"><h2>结论</h2><div class="cards">{cards}</div></section>')
    w = bz['wuxing']
    rows = [
        f'<tr><td class="k">日干</td><td>{E(bz["day_stems"]["pair"])}</td><td>{E("；".join(bz["day_stems"]["relation"]))}；{E(bz["day_stems"]["sheng_ke"])}；甲方看乙方是{E(bz["day_stems"]["a_sees_b"])}，乙方看甲方是{E(bz["day_stems"]["b_sees_a"])}</td></tr>',
        f'<tr><td class="k">日支（配偶宫）</td><td>{E(bz["day_branches"]["pair"])}</td><td>{E("；".join(bz["day_branches"]["relation"]))}</td></tr>',
        f'<tr><td class="k">年支（生肖）</td><td>{E(bz["year_branches"]["pair"])}</td><td>{E("；".join(bz["year_branches"]["relation"]))}</td></tr>',
        f'<tr><td class="k">夫妻星</td><td></td><td>{E(bz["spouse_star"]["a"])}；{E(bz["spouse_star"]["b"])}</td></tr>',
        f'<tr><td class="k">五行互补</td><td></td><td>甲方喜{E("".join(w["a_xi"]))}，乙方最旺{E("".join(w["b_strong"]))}，甲方得到{E("".join(w["a_gets"]) or "无")}；'
        f'乙方喜{E("".join(w["b_xi"]))}，甲方最旺{E("".join(w["a_strong"]))}，乙方得到{E("".join(w["b_gets"]) or "无")}</td></tr>',
    ]
    S.append(f'<section id="bazi"><h2>八字对照</h2>{_table(["项目", "双方", "关系"], rows)}<div class="prose">{_paras((nar.get("bazi") or ""))}</div></section>')
    if zw:
        fly = lambda xs: '，'.join(f'{x["star"]}{x["hua"]}入{x["palace"]}' for x in xs)  # noqa: E731
        rows = [f'<tr><td class="k">命宫</td><td>{E(zw["ming_branches"]["pair"])}</td><td>{E("；".join(zw["ming_branches"]["relation"]))}</td></tr>',
                f'<tr><td class="k">甲方四化入乙方</td><td></td><td>{E(fly(zw["a_to_b"]))}</td></tr>',
                f'<tr><td class="k">乙方四化入甲方</td><td></td><td>{E(fly(zw["b_to_a"]))}</td></tr>',
                f'<tr><td class="k">命宫对夫妻宫</td><td></td><td>甲方命宫 {E(zw["a_ming_vs_b_spouse"]["a_ming"])} 对乙方夫妻宫 {E(zw["a_ming_vs_b_spouse"]["b_spouse"])}；乙方命宫 {E(zw["b_ming_vs_a_spouse"]["b_ming"])} 对甲方夫妻宫 {E(zw["b_ming_vs_a_spouse"]["a_spouse"])}</td></tr>']
        S.append(f'<section id="ziwei"><h2>紫微对照</h2>{_table(["项目", "双方", "关系"], rows)}<div class="prose">{_paras((nar.get("ziwei") or ""))}</div></section>')
    for key, label in (('strengths', '合得来的地方'), ('frictions', '要磨合的地方'), ('advice', '相处建议')):
        if nar.get(key):
            S.append(f'<section id="{key}"><h2>{label}</h2><div class="prose"><ul>' + ''.join(f'<li>{E(x)}</li>' for x in nar[key]) + '</ul></div></section>')
    S.append('<section id="notes"><h2>说明</h2><div class="prose foot"><p>合盘只看两张盘在传统规则下的对照，不能决定一段关系的好坏。相处得怎样，取决于两个人的沟通、选择和经营。'
             '本报告仅供参考，不能替代婚恋、法律和心理方面的专业意见。</p></div></section>')
    title = nar.get('headline') or f"{A['name']} × {B['name']} 合盘"
    return ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{E(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<header class="top"><p class="eyebrow">合盘 · 八字 × 紫微斗数</p><h1>{E(title)}</h1></header>\n'
            f'<div class="layout" style="grid-template-columns:minmax(0,1fr)"><main>{"".join(S)}</main></div>\n</body>\n</html>\n')


def render_md(m: dict, nar: dict) -> str:
    nar = nar or {}
    L = [f"# {nar.get('headline') or (m['a']['name'] + ' × ' + m['b']['name'] + ' 合盘')}", '', brief(m), '']
    for c in nar.get('summary', []):
        L.append(f"- **{c.get('title')}**（{c.get('agree', '')}）：{c.get('text')}")
    for key, label in (('bazi', '八字对照解读'), ('ziwei', '紫微对照解读')):
        if nar.get(key):
            L += ['', f'## {label}', '', nar[key]]
    for key, label in (('strengths', '合得来的地方'), ('frictions', '要磨合的地方'), ('advice', '相处建议')):
        if nar.get(key):
            L += ['', f'## {label}', ''] + [f'- {x}' for x in nar[key]]
    L += ['', '> 合盘只看两张盘在传统规则下的对照，不能决定一段关系的好坏；仅供参考。']
    return '\n'.join(L)


def files(a_path: str, b_path: str) -> dict:
    return match(json.load(open(a_path, encoding='utf-8')), json.load(open(b_path, encoding='utf-8')))


__all__ = ['match', 'brief', 'render_html', 'render_md', 'files', '_md_table']
