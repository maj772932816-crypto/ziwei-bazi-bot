"""调用 crosscheck.cjs（lunar-javascript + iztro）并逐项比对。"""
import json
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_MAP = {}                                    # 本程序名 → iztro 名
# 截路空亡：本程序阴干年把正截、副截对调（与主流排盘软件一致），iztro 不对调；两星落在同一对宫位，按「这一宫有其中一颗」比
PAIR = {'截空': {'截路', '空亡'}, '副截': {'截路', '空亡'}}
SKIP = {'副旬'}                                  # iztro 不排的星


def case_from_facts(facts: dict, cid: str = 'chart', horoscope_dates=None) -> dict:
    import datetime as dt
    zw_date = facts['lunar']['from_date']
    clock = dt.datetime.fromisoformat(facts['input']['clock'])
    instant_bj = clock - dt.timedelta(hours=facts['input']['tz'] - 8)
    return {'id': cid, 'bazi_time': facts['input']['basis_time'], 'bazi_time_bj': instant_bj.strftime('%Y-%m-%d %H:%M'), 'ziwei_date': zw_date,
            'hour_idx': '子丑寅卯辰巳午未申酉戌亥'.index(facts['ziwei']['hour_branch']),
            'gender': facts['input']['gender'], 'zi_sect': facts['input']['zi_sect'],
            'horoscope_dates': list(horoscope_dates or [])}


def default_horoscope_dates(facts: dict) -> list:
    """核对运限用的日期：今天，以及逐年表里每年 7 月 1 日（避开起运前的童限）。"""
    import datetime as dt
    birth = facts['input']['birth_year_for_age']
    ju = facts['ziwei']['ju']
    days = [dt.date.today()] + [dt.date(r['year'], 7, 1) for r in facts.get('years', [])]
    return [d.isoformat() for d in days if d.year - birth + 1 >= ju + 1]


def compare_horoscope(facts: dict, ref: dict) -> list:
    import datetime as dt
    from .flow import at
    zw = facts['ziwei']
    by_name = {p['name']: p['branch'] for p in zw['palaces']}
    total = bad = 0
    diffs = []
    for h in ref.get('horoscope', []):
        mine = at(facts, dt.date.fromisoformat(h['date']))
        y, mo = mine['ziwei']['year'], mine['ziwei']['month']
        pairs = [
            ('大限', by_name.get(y['daxian_palace'], ''), h['decadal']),
            ('流年命宫', y['ming_branch'], h['yearly']),
            ('流年干支', y['gz'], h['yearly_gz']),
            ('小限', by_name.get(y['xiaoxian_palace'], ''), h['age']),
            ('虚岁', y['age_xu'], h['nominal_age']),
            ('流月命宫', mo['branch'], h['monthly']),
            ('流月干支', mo['gz'], h['monthly_gz']),
            ('流月四化', [s['star'] for s in mo['sihua']], h['monthly_mutagen']),
            ('八字流月', mine['bazi']['pillar'], h['bazi_month']),
        ]
        for label, a, b in pairs:
            total += 1
            if a != b:
                bad += 1
                diffs.append(f"{h['date']} {label}（本程序 {a}，对照 {b}）")
    if not total:
        return []
    return [{'item': '运限（大限、流年、小限、流月、八字流月）', 'status': 'ok' if bad == 0 else 'fail',
             'result': f'{total - bad} / {total} 项一致' + ('' if not diffs else '；不一致：' + '、'.join(diffs[:5])),
             'method': f"抽查 {len(ref.get('horoscope', []))} 个日期，与 iztro、lunar-javascript 比对"}]


def run_node(cases: list, scripts_dir: str = HERE) -> list:
    node = shutil.which('node')
    if not node:
        raise RuntimeError('没有 node，无法交叉核对；可安装 Node.js 18+ 后在 scripts 目录运行 npm install')
    if not os.path.isdir(os.path.join(scripts_dir, 'node_modules', 'iztro')):
        raise RuntimeError('缺少 iztro / lunar-javascript：请在 scripts 目录运行 npm install')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(cases, f, ensure_ascii=False)
        path = f.name
    try:
        res = subprocess.run([node, os.path.join(scripts_dir, 'crosscheck.cjs'), path],
                             capture_output=True, text=True, timeout=600, cwd=scripts_dir)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip()[:500])
        return json.loads(res.stdout)
    finally:
        os.unlink(path)


def _minutes_to_jie(facts: dict) -> float:
    import datetime as dt
    from .astro import from_bj, jie_around
    clock = dt.datetime.fromisoformat(facts['input']['clock'])
    inst = from_bj(clock - dt.timedelta(hours=facts['input']['tz'] - 8))
    j = jie_around(inst)
    return min(abs(float(j['prev'][1]) - float(inst)), abs(float(j['next'][1]) - float(inst))) * 1440


def compare(facts: dict, ref: dict) -> list:
    import datetime as dt
    checks = []
    bz = facts['bazi']
    if 'pillars' in ref:
        near = _minutes_to_jie(facts) < 2  # 节气前后 2 分钟内：两套天文算法的节气时刻相差几秒，属正常误差
        tol = 'warn' if near else 'fail'
        why = '；出生时刻离节气不到 2 分钟，两种算法的节气时刻相差几秒，属于正常误差，以出生证明的精确时间和本程序为准' if near else ''
        same = ref['pillars'] == bz['pillars']
        checks.append({'item': '八字四柱', 'status': 'ok' if same else tol,
                       'result': ' '.join(bz['pillars']) + ('' if same else f"（lunar-javascript：{' '.join(ref['pillars'])}{why}）"),
                       'method': '本程序天文算法 vs lunar-javascript'})
        diff = abs((dt.date.fromisoformat(ref['yun_start']) - dt.date.fromisoformat(bz['yun']['start_date'])).days)
        checks.append({'item': '起运', 'status': 'ok' if diff <= 5 else 'warn',
                       'result': f"{bz['yun']['start_date']}（约 {bz['yun']['start_age']} 岁）",
                       'method': f"lunar-javascript 为 {ref['yun_start']}，相差 {diff} 天" + ('（取整方式不同）' if diff <= 5 else why or '')})
        mine = [d['pillar'] for d in bz['dayun'][:8]]
        checks.append({'item': '大运', 'status': 'ok' if mine == ref['dayun'] else tol,
                       'result': ' '.join(mine) + ('' if mine == ref['dayun'] else why), 'method': '本程序 vs lunar-javascript'})
    if 'lunar' in ref:
        L = facts['lunar']
        same = (L['year'], L['month'], L['day'], L['leap']) == (ref['lunar']['year'], ref['lunar']['month'], ref['lunar']['day'], ref['lunar']['leap'])
        checks.append({'item': '农历日期', 'status': 'ok' if same else 'fail', 'result': L['text'],
                       'method': '本程序天文推算（朔日+中气）vs lunar-javascript'})
    zw = facts.get('ziwei')
    if zw and 'ziwei' in ref:
        iz = ref['ziwei']
        by_b = {p['branch']: p for p in iz['palaces']}
        total = mism = 0
        diffs = []
        for p in zw['palaces']:
            q = by_b[p['branch']]
            for s in p['stars']:
                if s['name'] in SKIP:
                    continue
                total += 1
                if s['name'] in PAIR:
                    if not PAIR[s['name']] & set(q['stars']):
                        mism += 1
                        diffs.append(f"{s['name']}（本程序在{p['branch']}）")
                elif NAME_MAP.get(s['name'], s['name']) not in q['stars']:
                    mism += 1
                    diffs.append(f"{s['name']}（本程序在{p['branch']}）")
                if 'hua' in s and q['hua'].get(s['name']) != s['hua']:
                    mism += 1
                    diffs.append(f"{s['name']}化{s['hua']}")
            for k_mine, k_ref in (('长生', 'cs'), ('博士', 'bs'), ('将前', 'jq'), ('岁前', 'sq')):
                total += 1
                if p[k_mine] != q[k_ref]:
                    mism += 1
                    diffs.append(f"{p['branch']}{k_mine}")
            total += 3
            if p['xiaoxian_ages'][:3] != q['ages']:
                mism += 1
                diffs.append(f"{p['branch']}小限")
            if p['daxian'] != q['decadal']:
                mism += 1
                diffs.append(f"{p['branch']}大限")
            if p['name'] != q['name'] and not (p['name'] == '仆役' and q['name'] in ('交友', '仆役')):
                mism += 1
                diffs.append(f"{p['branch']}宫名")
        head_ok = (zw['ming_branch'] == iz['soul'] and zw['shen_branch'] == iz['body'] and zw['ju_name'] == iz['ju']
                   and zw['mingzhu'] == iz['mingzhu'] and zw['shenzhu'] == iz['shenzhu'])
        checks.append({'item': '紫微命宫、身宫、五行局、命主身主', 'status': 'ok' if head_ok else 'fail',
                       'result': f"命宫{zw['ming_branch']}，身宫{zw['shen_branch']}（{zw['shen_palace']}），{zw['ju_name']}，命主{zw['mingzhu']}，身主{zw['shenzhu']}",
                       'method': '本程序安星 vs iztro'})
        checks.append({'item': '紫微全盘星曜与十二神', 'status': 'ok' if mism == 0 else 'fail',
                       'result': f'{total - mism} / {total} 项一致' + ('' if not diffs else '；不一致：' + '、'.join(diffs[:8])),
                       'method': '每颗星的落宫、生年四化、长生/博士/将前/岁前、大限、小限，与 iztro 逐项比对'})
        checks.extend(compare_horoscope(facts, ref))
    return checks
