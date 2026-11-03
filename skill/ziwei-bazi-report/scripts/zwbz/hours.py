"""出生时间不确定时：把候选时辰各排一张盘，列出彼此不同的地方，供用户按经历来选（定时辰）。

日期、性别、出生地不变；八字年月日三柱和大运通常不变，变的是时柱和整张紫微盘。
"""
import datetime as dt

from . import bazi, engine

BR = bazi.BRANCHES
KEY_PALACES = ['命宫', '兄弟', '夫妻', '子女', '财帛', '官禄', '田宅', '父母']


def _majors(p):
    return '、'.join(s['name'] + (f"化{s['hua']}" if 'hua' in s else '') for s in p['stars'] if s['type'] == 'major') or '空宫'


def candidates(date: str, gender: str, *, around: str = None, all_hours: bool = False, **kw) -> dict:
    """around='HH:MM'：取所在时辰和交界另一侧的时辰；all_hours=True：十二个时辰都排。"""
    probe = engine.build(date, around or '12:00', gender, years_count=1, **kw)
    off = dt.timedelta(0)
    if probe['input']['basis_time'] and probe['input']['clock']:
        off = (dt.datetime.fromisoformat(probe['input']['basis_time']) - dt.datetime.fromisoformat(probe['input']['clock']))
    if all_hours:
        branches = list(range(12))
    else:
        b0 = BR.index(probe['ziwei']['hour_branch'])
        _, other = engine._hour_boundary_minutes(dt.datetime.fromisoformat(probe['input']['basis_time']))
        branches = [b0, BR.index(other)]
    base_day = dt.datetime.fromisoformat(probe['input']['clock']).date() if probe['input']['clock'] else dt.date.fromisoformat(probe['input']['solar_date'])
    rows = []
    for b in branches:
        center = dt.datetime(base_day.year, base_day.month, base_day.day) + dt.timedelta(hours=2 * b)
        clock = center - off
        f = engine.build(clock.strftime('%Y-%m-%d'), clock.strftime('%H:%M'), gender, years_count=1,
                         **{k: v for k, v in kw.items() if k not in ('calendar', 'leap', 'dst_adjust')})
        zw = f['ziwei']
        by = {p['name']: p for p in zw['palaces']}
        now_age = f['years'][0]['age_xu'] if f['years'] else None
        dx = [{'range': p['daxian'], 'palace': p['name'], 'majors': _majors(p)} for p in sorted(zw['palaces'], key=lambda x: x['daxian'][0])[:7]]
        rows.append({
            'hour': BR[b] + '时', 'clock_example': clock.strftime('%H:%M'), 'hour_pillar': f['bazi']['pillars'][3],
            'ming': f"{zw['palaces'][0]['stem']}{zw['ming_branch']} {_majors(zw['palaces'][0])}", 'shen': zw['shen_palace'],
            'ju': zw['ju_name'], 'palaces': {k: _majors(by[k]) for k in KEY_PALACES},
            'daxian': dx, 'now_daxian': next((f"{d['range'][0]}–{d['range'][1]} {d['palace']}（{d['majors']}）" for d in dx
                                              if now_age and d['range'][0] <= now_age <= d['range'][1]), ''),
            'dataset_key': f.get('dataset_key'),
        })
    diffs = [k for k in KEY_PALACES if len({r['palaces'][k] for r in rows}) > 1]
    return {'date': date, 'gender': gender, 'candidates': rows, 'differs_in': diffs,
            'note': '日期、性别、出生地相同；候选时辰的代表时间取时辰正中（已换算回钟表时间）'}


def brief(h: dict) -> str:
    L = [f"定时辰：{h['date']}，{'男' if engine.parse_gender(h['gender']) == 'male' else '女'}；{h['note']}"]
    for r in h['candidates']:
        L.append(f"【{r['hour']}】（钟表约 {r['clock_example']}）时柱{r['hour_pillar']}；命宫 {r['ming']}；身宫在{r['shen']}；{r['ju']}；当前大限 {r['now_daxian']}")
        L.append('  ' + '；'.join(f"{k} {v}" for k, v in r['palaces'].items()))
        L.append('  大限：' + '；'.join(f"{d['range'][0]}–{d['range'][1]} {d['palace']}（{d['majors']}）" for d in r['daxian']))
    L.append('差别最大的宫位：' + ('、'.join(h['differs_in']) or '无'))
    L.append('用法：按差别最大的宫位和各大限的时间段，问用户几件可以核对的往事（父母、兄弟、配偶的特点，十几岁和二十几岁时的大事），选最贴合的时辰再正式排盘。')
    return '\n'.join(L)
