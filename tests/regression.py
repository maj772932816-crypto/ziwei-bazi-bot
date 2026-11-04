#!/usr/bin/env python3
"""回归测试：固定的虚构出生信息，排盘结果必须和 golden.json 完全一样（防止改代码时无意改动结果）。

  python3 tests/regression.py            # 比对
  python3 tests/regression.py --update   # 确认结果正确后，重写 golden.json
golden.json 第一次生成时，已用 iztro、lunar-javascript 交叉核对过（见 zwbz selftest）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'skill', 'ziwei-bazi-report', 'scripts'))

from zwbz import engine  # noqa: E402
from zwbz.flow import at  # noqa: E402
from zwbz.lint import lint  # noqa: E402

CASES = [  # 全部是虚构的出生信息
    dict(date='1990-05-20', time='14:30', gender='女', city='杭州'),
    dict(date='1985-02-03', time='23:40', gender='男', city='成都'),
    dict(date='2004-06-25', time='05:05', gender='女', city='哈尔滨'),
    dict(date='1966-03-20', time='12:00', gender='男', calendar='lunar', leap=True),
    dict(date='2012-12-21', time='00:30', gender='男', lon=-74.0, tz=-5, city='纽约'),
]
GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golden.json')


def snapshot(c: dict) -> dict:
    f = engine.build(**c, years_from=2026, years_count=1)
    zw = f['ziwei']
    day = at(f, __import__('datetime').date(2026, 11, 3))
    return {
        'basis_time': f['input']['basis_time'], 'lunar': f['lunar']['text'], 'pillars': f['bazi']['pillars'],
        'yun_start': f['bazi']['yun']['start_date'], 'dayun': [d['pillar'] for d in f['bazi']['dayun'][:4]],
        'ming': zw['palaces'][0]['stem'] + zw['ming_branch'], 'shen': zw['shen_palace'], 'ju': zw['ju_name'],
        'palaces': {p['branch']: sorted(s['name'] + s.get('hua', '') for s in p['stars']) for p in zw['palaces']},
        'issues': sorted(i['code'] for i in f['issues']), 'status': f['status']['status'], 'dataset_key': f.get('dataset_key'),
        '2026-11-03': {'year': day['ziwei']['year']['ming_palace'], 'daxian': day['ziwei']['year']['daxian_palace'],
                       'xiaoxian': day['ziwei']['year']['xiaoxian_palace'], 'month': day['ziwei']['month']['palace'],
                       'bazi_month': day['bazi']['pillar']},
    }


def main():
    snaps = {json.dumps(c, ensure_ascii=False, sort_keys=True): snapshot(c) for c in CASES}
    if '--update' in sys.argv:
        json.dump(snaps, open(GOLDEN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        print(f'已更新 {GOLDEN}（{len(snaps)} 个案例）')
        return
    golden = json.load(open(GOLDEN, encoding='utf-8'))
    bad = 0
    for k, v in snaps.items():
        if golden.get(k) != v:
            bad += 1
            g = golden.get(k, {})
            diff = [f for f in v if g.get(f) != v[f]]
            print('不一致：', k, '字段', diff)
    ex = os.path.join(ROOT, 'skill', 'ziwei-bazi-report', 'references', 'example-narrative.json')
    f = engine.build('1990-05-20', '14:30', '女', city='杭州', years_from=2026, years_count=6)
    errs = [x for x in lint(f, json.load(open(ex, encoding='utf-8'))) if x['level'] == 'error']
    if errs:
        bad += 1
        print('示例解读没有通过检查：', errs[:2])
    # 合盘解读检查：写错命宫关系、写错四化落宫都要被抓到
    from zwbz.lint import lint_match
    from zwbz.match import match
    m = match(f, engine.build('1988-08-08', '08:08', '男', city='北京', dst_adjust=True, years_count=1))
    wrong = {'ziwei': '命宫戌卯六合；甲方生年太阴化科入乙方命宫、天同化忌入乙方迁移。', 'advice': ['你们八字不合']}
    caught = len([x for x in lint_match(m, wrong) if x['level'] == 'error'])
    if caught < 4:
        bad += 1
        print('合盘检查漏报：只抓到', caught, '处')
    # 聊天回复检查（1.1.1）：Grok 实测中写错的原句要被抓到，改正后的写法不能误报
    from zwbz.lint import lint_text
    a10 = engine.build('1990-05-20', '14:30', '女', city='杭州', years_from=2026, years_count=10)
    b10 = engine.build('1988-08-08', '08:08', '男', city='北京', dst_adjust=True, years_from=2026, years_count=10)
    text_cases = [
        (a10, '2025 到 2035 这十年，两边都指向责任重、压力大，2035 年后倾向转顺。', None, 'error', 1),
        (a10, '天机化忌入命宫，容易想太多，生年天机自化权就带这个倾向。', '2026-11-03', 'error', 1),
        (b10, '这十年（约 2018 到 2028）的重心在家庭、房子和文书资产上。', None, 'warn', 1),
        (b10, '紫微田宅大限（2018–2028）重心在家庭和房子。', None, 'error', 1),
        (a10, '八字丁丑运（2025–2035）和紫微子女大限（2024–2033）都是压力最重的一段；命宫天机自化权。', None, 'any', 0),
        (a10, '太阴化权入财帛，倾向主动管钱；天机化忌入命宫。', '2026-11-03', 'any', 0),
    ]
    text_ok = 0
    for f_, t, d, level, want in text_cases:
        fs = lint_text(f_, t, d)
        got = len(fs) if level == 'any' else len([x for x in fs if x['level'] == level])
        if got == want:
            text_ok += 1
        else:
            print('聊天回复检查不符：', t[:30], '期望', want, '实际', got, [x['message'][:60] for x in fs])
    if text_ok < len(text_cases):
        bad += 1
    # 详版（1.2.0）：宫位语境、宫名、完整性
    pal_cases = [
        ({'ziwei': {'palaces': {'夫妻': '天机坐守，想得多。'}}}, 'error', 1),
        ({'ziwei': {'palaces': {'迁移': '空宫，借对宫命宫的天机天梁坐守。'}}}, 'error', 0),
        ({'ziwei': {'palaces': {'命宫': '本宫是空宫。', '财务': '无'}}}, 'error', 2),
        ({'detail': 'full', 'ziwei': {'palaces': {'命宫': '天机天梁同宫。'}}}, 'warn', 4),
    ]
    for nar_, level, want in pal_cases:
        got = len([x for x in lint(a10, nar_) if x['level'] == level and not x['message'].startswith('缺少')])
        if got == want:
            text_ok += 1
        else:
            bad += 1
            print('详版检查不符：', nar_, '期望', want, '实际', got)
    text_cases += pal_cases
    print(f'回归测试：{len(snaps)} 个案例' + ('全部一致' if not bad else f'，{bad} 处不一致') + '；示例解读检查' + ('通过' if not errs else '未通过')
          + f'；合盘检查抓到 {caught}/4 处；聊天回复和详版检查 {text_ok}/{len(text_cases)} 条符合')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
