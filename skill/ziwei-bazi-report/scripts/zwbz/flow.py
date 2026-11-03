"""逐年表与流月：八字流年/流月与原局、大运的作用；紫微流年命宫、流月命宫（流年斗君起正月）、四化落宫、大限、小限。

虚岁按农历年计（出生那年的农历年为 1 岁，正月初一加一岁），与紫微排大限、小限的口径一致。
"""
import datetime as dt

from . import bazi
from .astro import JIE, from_bj, jie_around, lichun, term_time, to_bj
from .lunar import MONTH_NAMES, _entries, solar_to_lunar
from .ziwei import SIHUA, liunian, palace_of

ST, BR = bazi.STEMS, bazi.BRANCHES


def current_dayun(dayun: list, when: str):
    """when：'YYYY-MM-DD' 或年份字符串；返回当时所在的大运。"""
    cur = None
    for d in dayun:
        if d['start'] <= when:
            cur = d
    return cur


def _new_relations(stems: dict, branches: dict, key: str, stem: str, branch: str) -> list:
    base = set(bazi.relations(stems, branches))
    rel = bazi.relations({**stems, key: stem}, {**branches, key: branch})
    return [r for r in rel if r not in base]


def _natal(bz: dict):
    labels = ['年', '月', '日', '时'][: len(bz['pillars'])]
    return ({f'原局{labels[i]}': p[0] for i, p in enumerate(bz['pillars'])},
            {f'原局{labels[i]}': p[1] for i, p in enumerate(bz['pillars'])})


def year_rows(facts: dict, first: int, count: int) -> list:
    bz = facts['bazi']
    dm = bz['day_master']
    birth = facts['input']['birth_year_for_age']
    rows = []
    for y in range(first, first + count):
        g = bazi.gz((y - 4) % 60)
        dy = current_dayun(bz['dayun'], f'{y}-07-01')
        stems, branches = _natal(bz)
        if dy:
            stems['大运'], branches['大运'] = dy['pillar'][0], dy['pillar'][1]
        row = {
            'year': y, 'gz': g, 'age_xu': y - birth + 1, 'dayun': dy['pillar'] if dy else '',
            'gods': f"{bazi.ten_god(dm, g[0])} / {bazi.ten_god(dm, bazi.HIDDEN[g[1]][0])}",
            'bazi_relations': _new_relations(stems, branches, '流年', g[0], g[1]),
        }
        zw = facts.get('ziwei')
        if zw:
            row['ziwei'] = liunian(zw, y, birth, zw['lunar_month_used'], BR.index(zw['hour_branch']))
        rows.append(row)
    return rows


def doujun(zw: dict, lunar_year: int) -> int:
    """流年斗君（流月正月所在地支序号）：从流年太岁宫起正月逆数到生月，再从该宫起子时顺数到生时。"""
    return ((lunar_year - 4) % 12 - (zw['lunar_month_used'] - 1) + BR.index(zw['hour_branch'])) % 12


def ziwei_month(zw: dict, lunar_year: int, month: int) -> dict:
    ys = (lunar_year - 4) % 10
    yin = ((ys % 5) * 2 + 2) % 10
    b = (doujun(zw, lunar_year) + month - 1) % 12
    stem = ST[(yin + month - 1) % 10]
    names = {p['branch']: p['name'] for p in zw['palaces']}
    hua = dict(zip('禄权科忌', SIHUA[stem].split()))
    return {'month': month, 'gz': stem + BR[(2 + month - 1) % 12], 'branch': BR[b], 'palace': names[BR[b]],
            'sihua': [{'hua': k, 'star': s, 'palace': palace_of(zw, s)} for k, s in hua.items()]}


def bazi_month(facts: dict, start: dt.datetime, pillar: str, flow_year_gz: str) -> dict:
    bz = facts['bazi']
    dm = bz['day_master']
    stems, branches = _natal(bz)
    dy = current_dayun(bz['dayun'], start.strftime('%Y-%m-%d'))
    if dy:
        stems['大运'], branches['大运'] = dy['pillar'][0], dy['pillar'][1]
    stems['流年'], branches['流年'] = flow_year_gz[0], flow_year_gz[1]
    return {'pillar': pillar, 'gods': f"{bazi.ten_god(dm, pillar[0])} / {bazi.ten_god(dm, bazi.HIDDEN[pillar[1]][0])}",
            'relations': _new_relations(stems, branches, '流月', pillar[0], pillar[1]), 'dayun': dy['pillar'] if dy else ''}


def month_rows(facts: dict, year: int) -> dict:
    """某一年的流月：八字按节气月（立春起），紫微按农历月（正月起；闰月按本命盘同一规则，默认前十五天算本月、后半月算下月）。"""
    out = {'year': year, 'bazi': [], 'ziwei': []}
    ys = (year - 4) % 10
    yin = ((ys % 5) * 2 + 2) % 10
    t0 = lichun(year)
    starts = [term_time(deg, float(t0) + 30.44 * k) for k, (deg, _) in enumerate(JIE)] + [lichun(year + 1)]
    flow_gz = bazi.gz((year - 4) % 60)
    for k in range(12):
        s, e = to_bj(starts[k]), to_bj(starts[k + 1])
        pillar = ST[(yin + k) % 10] + BR[(2 + k) % 12]
        row = bazi_month(facts, s, pillar, flow_gz)
        row.update({'jie': JIE[k][1], 'start': s.strftime('%Y-%m-%d %H:%M'), 'end': e.strftime('%Y-%m-%d %H:%M')})
        out['bazi'].append(row)
    zw = facts.get('ziwei')
    if zw:
        for y0 in (year - 1, year):
            for st, ly, n, lp, days in _entries(y0):
                if ly != year:
                    continue
                label = f"{'闰' if lp else ''}{MONTH_NAMES[n - 1]}月"
                spans = [(1, days, n)]
                if lp:
                    policy = facts['input'].get('leap_policy', 'split')
                    if policy == 'split':
                        spans = [(1, min(15, days), n), (16, days, n % 12 + 1)]
                    elif policy == 'next':
                        spans = [(1, days, n % 12 + 1)]
                for a, b, mm in spans:
                    if a > b:
                        continue
                    row = ziwei_month(zw, year, mm)
                    part = '' if len(spans) == 1 else ('（前半，按本月）' if a == 1 else '（后半，按下月）')
                    row.update({'label': label + part, 'leap': lp,
                                'start': (st + dt.timedelta(days=a - 1)).isoformat(), 'end': (st + dt.timedelta(days=b - 1)).isoformat()})
                    out['ziwei'].append(row)
    return out


def at(facts: dict, day: dt.date) -> dict:
    """某一天：八字的流年、流月（节气月），紫微的大限、流年、小限、流月（农历月）。"""
    bz = facts['bazi']
    noon = from_bj(dt.datetime(day.year, day.month, day.day, 12))
    fy = day.year if noon >= lichun(day.year) else day.year - 1
    k = jie_around(noon)['month_index']
    ys = (fy - 4) % 10
    pillar = ST[(((ys % 5) * 2 + 2) % 10 + k) % 10] + BR[(2 + k) % 12]
    flow_gz = bazi.gz((fy - 4) % 60)
    res = {'date': day.isoformat(), 'bazi': {'flow_year': flow_gz, **bazi_month(facts, to_bj(noon), pillar, flow_gz)}}
    dm = bz['day_master']
    res['bazi']['flow_year_gods'] = f"{bazi.ten_god(dm, flow_gz[0])} / {bazi.ten_god(dm, bazi.HIDDEN[flow_gz[1]][0])}"
    zw = facts.get('ziwei')
    if zw:
        L = solar_to_lunar(day)
        birth = facts['input']['birth_year_for_age']
        ln = liunian(zw, L.year, birth, zw['lunar_month_used'], BR.index(zw['hour_branch']))
        mm = L.month
        if L.leap:
            policy = facts['input'].get('leap_policy', 'split')
            if policy == 'next' or (policy == 'split' and L.day > 15):
                mm = L.month % 12 + 1
        mo = ziwei_month(zw, L.year, mm)
        mo['label'] = f"{'闰' if L.leap else ''}{MONTH_NAMES[L.month - 1]}月" + (f'（按{MONTH_NAMES[mm - 1]}月）' if mm != L.month else '')
        res['ziwei'] = {'lunar': L.text(), 'year': ln, 'month': mo}
    return res
