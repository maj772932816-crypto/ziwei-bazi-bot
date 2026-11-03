#!/usr/bin/env python3
"""紫微斗数 + 八字：排盘、交叉核对、查数据集、检查解读、出报告。

常用：
  zwbz run --date 1990-05-20 --time 14:30 --gender 女 --city 杭州            # 一条命令：排盘+核对+数据集+要点
  zwbz lint  work/<编号>/facts.json work/<编号>/narrative.json             # 检查解读有没有说错
  zwbz render work/<编号>/facts.json work/<编号>/narrative.json             # 生成 report.html（先自动 lint）
  zwbz render ... --format md / --format chat                             # Markdown 完整版 / 聊天短摘要
  zwbz month work/<编号>/facts.json --date 2026-11-03                      # 某一天所在的流月、流年、大限
  zwbz match work/A/facts.json work/B/facts.json                           # 合盘（解读写好后 render-match，会先自动检查）
  zwbz hours --date 1990-05-20 --gender 女 --city 杭州 --around 14:55       # 出生时间不确定时对照相邻时辰
  zwbz purge work/<编号>                                                   # 删除某个用户的全部数据
  zwbz selftest                                                           # 环境自检

（zwbz 指 scripts/zwbz.sh 包装脚本，会优先用 install.sh 建的虚拟环境；也可以直接 python3 scripts/zwbz.py ...）
退出码：run 0=可以继续，3=先问用户，4=停下；lint 1=有错误。
"""
import argparse
import datetime as dt
import json
import os
import random
import secrets
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from zwbz import __version__, engine  # noqa: E402
from zwbz.brief import brief  # noqa: E402

EXIT = {'ok': 0, 'confirm': 3, 'stop': 4}


def _save(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(obj, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        sys.exit(f'找不到文件：{path}')
    except json.JSONDecodeError as e:
        sys.exit(f'{path} 不是合法的 JSON：第 {e.lineno} 行第 {e.colno} 列，{e.msg}。改好再运行。')


def _crosscheck(facts):
    from zwbz.crosscheck import case_from_facts, compare, default_horoscope_dates, run_node
    if not facts.get('ziwei'):
        return facts
    try:
        ref = run_node([case_from_facts(facts, horoscope_dates=default_horoscope_dates(facts))])[0]
        facts['checks'].extend(compare(facts, ref))
    except Exception as e:  # noqa: BLE001
        facts['checks'].append({'item': '交叉核对', 'status': 'warn', 'result': f'没有运行：{e}', 'method': 'lunar-javascript、iztro'})
    return engine.refresh(facts)


def _dataset(facts, full_path=None):
    from zwbz import dataset
    key = facts.get('dataset_key')
    if not key:
        return facts
    if int(key[:4]) not in dataset.YEARS:
        facts['dataset'] = {'key': key, 'error': '数据集只覆盖 1950–2026 年出生'}
        return facts
    try:
        rec = dataset.lookup(key)
        if not rec:
            facts['dataset'] = {'key': key, 'error': '数据集里没有这一条'}
            return facts
        facts['dataset'] = {'key': key, 'dims': dataset.summarize(rec), 'attribution': dataset.ATTRIBUTION}
        if full_path:
            open(full_path, 'w', encoding='utf-8').write(dataset.to_markdown(rec))
            facts['dataset']['full_text_file'] = os.path.basename(full_path)
    except Exception as e:  # noqa: BLE001
        facts['dataset'] = {'key': key, 'error': f'查询失败：{e}'}
    return facts


def _build_kwargs(a):
    return dict(calendar='lunar' if a.lunar else 'solar', leap=a.leap, city=a.city or '', lon=a.lon, tz=a.tz,
                solar_time=not a.no_solar_time, dst_adjust=a.dst_adjust, zi_sect=a.zi_sect, leap_policy=a.leap_policy)


def cmd_run(a):
    out_dir = a.out or os.path.join('work', dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(2))
    if a.output:  # 兼容旧的 chart -o facts.json
        out_dir = os.path.dirname(os.path.abspath(a.output)) or '.'
    os.makedirs(out_dir, exist_ok=True)
    facts_path = a.output or os.path.join(out_dir, 'facts.json')
    facts = engine.build(a.date, a.time, a.gender, years_from=a.from_year, years_count=a.years,
                         months_year=a.months, name=a.name or '', **_build_kwargs(a))
    if not a.no_crosscheck:
        _crosscheck(facts)
    if not a.no_dataset:
        _dataset(facts, os.path.join(out_dir, 'facts.dataset.md'))
    engine.refresh(facts)
    _save(facts, facts_path)
    text = brief(facts)
    open(os.path.join(out_dir, 'brief.txt'), 'w', encoding='utf-8').write(text)
    _save(facts['status'], os.path.join(out_dir, 'status.json'))
    print(text)
    st = facts['status']
    print(f"\n工作目录：{out_dir}\n状态：{st['status']}（{st['next']}）")
    for q in st['questions']:
        print('要问用户：' + q)
    sys.exit(EXIT[st['status']])


def cmd_brief(a):
    print(brief(_load(a.facts)))


def cmd_lint(a):
    from zwbz.lint import lint, report
    findings = lint(_load(a.facts), _load(a.narrative))
    print(report(findings))
    sys.exit(1 if any(f['level'] == 'error' for f in findings) else 0)


def cmd_render(a):
    from zwbz.lint import lint, report
    from zwbz.report import render_files
    facts = _load(a.facts)
    if a.narrative:
        findings = lint(facts, _load(a.narrative))
        if findings:
            print(report(findings))
        if any(f['level'] == 'error' for f in findings) and not a.force:
            print('解读里有与排盘结果矛盾的地方，没有生成报告。改正后再运行（确有把握时可加 --force）。')
            sys.exit(1)
    st = facts.get('status', {}).get('status')
    if st == 'stop' and not a.force:
        print('这张盘的核对没有通过（status=stop），不生成报告。')
        sys.exit(4)
    out = a.output or os.path.join(os.path.dirname(os.path.abspath(a.facts)), {'html': 'report.html', 'md': 'report.md', 'chat': 'chat.txt'}[a.format])
    text = render_files(a.facts, a.narrative, out, a.format)
    if a.format == 'chat':
        print(text)
    print('已生成', out)


def cmd_month(a):
    from zwbz.flow import at, month_rows
    facts = _load(a.facts)
    if a.year:
        facts['months'] = month_rows(facts, a.year)
        if a.save:
            _save(facts, a.facts)
        text = brief(facts)
        print(text[text.index('【流月'):].split('【开源数据集')[0].rstrip())
        if a.save:
            print('已写回', a.facts, '（render 时报告里会多一节流月）')
        return
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    r = at(facts, day)
    b = r['bazi']
    print(f"{r['date']}：八字流年 {b['flow_year']}（{b['flow_year_gods']}），流月 {b['pillar']}（{b['gods']}），大运 {b['dayun']}；"
          + ('；'.join(b['relations']) or '流月与原局无明显作用'))
    if 'ziwei' in r:
        z = r['ziwei']
        y, mo = z['year'], z['month']
        print(f"紫微：农历 {z['lunar']}；虚岁 {y['age_xu']}，大限 {y['daxian_palace']} {y['daxian']}，流年命宫在{y['ming_palace']}（{y['gz']}），小限 {y['xiaoxian_palace']}；"
              f"流年四化 " + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in y['sihua']))
        print(f"  流月 {mo['label']}（{mo['gz']}）：流月命宫在{mo['palace']}；" + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in mo['sihua']))


def cmd_match(a):
    from zwbz import match
    m = match.files(a.a, a.b)
    out = a.output or os.path.join(os.path.dirname(os.path.abspath(a.a)), 'match.json')
    _save(m, out)
    print(match.brief(m))
    print('\n已保存', out)


def cmd_lint_match(a):
    from zwbz.lint import lint_match, report
    findings = lint_match(_load(a.match), _load(a.narrative))
    print(report(findings))
    sys.exit(1 if any(f['level'] == 'error' for f in findings) else 0)


def cmd_render_match(a):
    from zwbz import match
    from zwbz.lint import lint_match, report
    m = _load(a.match)
    nar = _load(a.narrative) if a.narrative else {}
    if nar:
        findings = lint_match(m, nar)
        if findings:
            print(report(findings))
        if any(f['level'] == 'error' for f in findings) and not a.force:
            print('合盘解读里有与对照结果矛盾的地方，没有生成报告。改正后再运行（确有把握时可加 --force）。')
            sys.exit(1)
    text = (match.render_html if a.format == 'html' else match.render_md)(m, nar)
    out = a.output or os.path.join(os.path.dirname(os.path.abspath(a.match)), 'match.' + ('html' if a.format == 'html' else 'md'))
    open(out, 'w', encoding='utf-8').write(text)
    print('已生成', out)


def cmd_hours(a):
    from zwbz import hours
    h = hours.candidates(a.date, a.gender, around=a.around, all_hours=a.all, **_build_kwargs(a))
    print(hours.brief(h))
    if a.output:
        _save(h, a.output)
        print('已保存', a.output)


def cmd_purge(a):
    removed = []
    targets = list(a.paths)
    if a.older_than is not None:
        root = a.root
        cutoff = dt.datetime.now().timestamp() - a.older_than * 86400
        if os.path.isdir(root):
            targets += [os.path.join(root, d) for d in os.listdir(root) if os.path.getmtime(os.path.join(root, d)) < cutoff]
    for t in targets:
        if not os.path.isdir(t) or not any(os.path.exists(os.path.join(t, n)) for n in ('facts.json', 'match.json', 'hours.json', 'status.json')):
            print('跳过（不是本工具生成的工作目录）：', t)
            continue
        shutil.rmtree(t)
        removed.append(t)
    print(f'已删除 {len(removed)} 个工作目录' + ('：' + '、'.join(removed) if removed else ''))


def cmd_selftest(a):
    from zwbz.crosscheck import case_from_facts, compare, run_node
    from zwbz.lint import lint
    rnd = random.Random(a.seed)
    facts_list, cases = [], []
    for k in range(a.n):
        t = dt.datetime(1950, 1, 1) + dt.timedelta(minutes=rnd.randrange(0, 75 * 365 * 24 * 60))
        f = engine.build(t.strftime('%Y-%m-%d'), t.strftime('%H:%M'), rnd.choice(['男', '女']), years_count=1)
        ju = f['ziwei']['ju']
        dates = [(t.date() + dt.timedelta(days=rnd.randrange((ju + 1) * 366, 80 * 365))).isoformat() for _ in range(3)]
        facts_list.append(f)
        cases.append(case_from_facts(f, str(k), [d for d in dates if d < '2100']))
    refs = run_node(cases)
    bad = 0
    for f, r in zip(facts_list, refs):
        fails = [c for c in compare(f, r) if c['status'] == 'fail']
        if fails:
            bad += 1
            if bad <= 5:
                print('不一致：', f['input']['clock'], f['input']['gender'], fails[0]['item'], fails[0]['result'][:160])
    print(f'排盘自检 {a.n} 张随机盘（含运限抽查）：{a.n - bad} 张与 lunar-javascript / iztro 完全一致，{bad} 张有差异')
    # 解读检查自检：示例解读应通过，故意写错的应被抓到
    ex = os.path.join(HERE, '..', 'references', 'example-narrative.json')
    f = engine.build('1990-05-20', '14:30', '女', city='杭州', years_from=2026, years_count=6)
    good = _load(ex)
    ok_good = not [x for x in lint(f, good) if x['level'] == 'error']
    wrong = json.loads(json.dumps(good))
    wrong['summary'][0]['text'] = '生年太阴化忌，紫微在命宫，日主甲，2027 年戊申，火六局。'
    caught = len([x for x in lint(f, wrong) if x['level'] == 'error'])
    print(f"解读检查自检：示例解读{'通过' if ok_good else '未通过'}，故意写错的 5 处抓到 {caught} 处")
    sys.exit(1 if bad or not ok_good or caught < 5 else 0)


def _add_birth_args(c, time_required=True):
    c.add_argument('--date', required=True, help='出生日期 YYYY-MM-DD（默认公历；农历加 --lunar）')
    c.add_argument('--time', required=time_required, default='unknown', help='出生时间 HH:MM（24 小时制）；不知道填 unknown')
    c.add_argument('--gender', required=True, help='男 / 女')
    c.add_argument('--city', help='出生城市，用于真太阳时，如 杭州、浙江杭州')
    c.add_argument('--lon', type=float, help='出生地经度（东经为正），找不到城市或海外出生时用')
    c.add_argument('--tz', type=float, default=8.0, help='出生地钟表时区，默认 8（北京时间）；纽约填 -5')
    c.add_argument('--lunar', action='store_true', help='输入的是农历日期')
    c.add_argument('--leap', action='store_true', help='农历闰月')
    c.add_argument('--no-solar-time', action='store_true', help='不做真太阳时校正')
    c.add_argument('--dst-adjust', action='store_true', help='出生在中国夏令时期间、记录的是当时钟表时间：减 1 小时')
    c.add_argument('--zi-sect', choices=['next', 'same'], default='next', help='晚子时：next=23 点换日（默认），same=日柱仍算当天')
    c.add_argument('--leap-policy', choices=['split', 'current', 'next'], default='split', help='闰月：split=前十五天本月、后半月下月（默认）')


def main():
    p = argparse.ArgumentParser(prog='zwbz', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version=f'zwbz {__version__}')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'chart'):
        c = sub.add_parser(name, help='排盘、交叉核对、查数据集，输出 facts.json 和要点' + ('（同 run）' if name == 'chart' else ''))
        _add_birth_args(c)
        c.add_argument('--from-year', type=int, help='逐年表起始年，默认今年')
        c.add_argument('--years', type=int, default=10, help='逐年表年数，默认 10')
        c.add_argument('--months', type=int, help='同时排这一年的流月，如 2026')
        c.add_argument('--name', help='称呼（可选，只用于报告标题）')
        c.add_argument('--out', help='工作目录，默认 work/<时间>-<随机码>')
        c.add_argument('-o', '--output', help='（兼容旧用法）facts.json 的路径')
        c.add_argument('--no-crosscheck', action='store_true', help='跳过交叉核对（不建议）')
        c.add_argument('--no-dataset', action='store_true', help='不查 13 维数据集')
        c.add_argument('--crosscheck', action='store_true', help=argparse.SUPPRESS)
        c.add_argument('--dataset', action='store_true', help=argparse.SUPPRESS)
        c.set_defaults(func=cmd_run)
    b = sub.add_parser('brief', help='打印给模型读的要点')
    b.add_argument('facts')
    b.set_defaults(func=cmd_brief)
    li = sub.add_parser('lint', help='检查解读有没有和排盘结果矛盾')
    li.add_argument('facts')
    li.add_argument('narrative')
    li.set_defaults(func=cmd_lint)
    r = sub.add_parser('render', help='生成报告（先自动 lint）')
    r.add_argument('facts')
    r.add_argument('narrative', nargs='?')
    r.add_argument('-o', '--output')
    r.add_argument('--format', choices=['html', 'md', 'chat'], default='html')
    r.add_argument('--force', action='store_true', help='lint 有错误或核对未通过时仍生成（不建议）')
    r.set_defaults(func=cmd_render)
    mo = sub.add_parser('month', help='流月：某一天（默认今天），或一整年')
    mo.add_argument('facts')
    mo.add_argument('--date')
    mo.add_argument('--year', type=int)
    mo.add_argument('--save', action='store_true', help='把整年流月写回 facts.json（报告里会多一节流月）')
    mo.set_defaults(func=cmd_month)
    m = sub.add_parser('match', help='合盘：两个人的 facts.json')
    m.add_argument('a')
    m.add_argument('b')
    m.add_argument('-o', '--output')
    m.set_defaults(func=cmd_match)
    rm = sub.add_parser('render-match', help='生成合盘报告')
    rm.add_argument('match')
    rm.add_argument('narrative', nargs='?')
    rm.add_argument('-o', '--output')
    rm.add_argument('--format', choices=['html', 'md'], default='html')
    rm.add_argument('--force', action='store_true', help='检查有错误时仍生成（不建议）')
    rm.set_defaults(func=cmd_render_match)
    lm = sub.add_parser('lint-match', help='检查合盘解读有没有和对照结果矛盾')
    lm.add_argument('match')
    lm.add_argument('narrative')
    lm.set_defaults(func=cmd_lint_match)
    h = sub.add_parser('hours', help='出生时间不确定：对照候选时辰')
    _add_birth_args(h, time_required=False)
    h.add_argument('--around', help='大概的出生时间 HH:MM：对照所在时辰和交界另一侧的时辰')
    h.add_argument('--all', action='store_true', help='十二个时辰都排')
    h.add_argument('-o', '--output')
    h.set_defaults(func=cmd_hours)
    pg = sub.add_parser('purge', help='删除工作目录（用户要求删除数据时）')
    pg.add_argument('paths', nargs='*')
    pg.add_argument('--older-than', type=int, help='删除 N 天前的工作目录')
    pg.add_argument('--root', default='work')
    pg.set_defaults(func=cmd_purge)
    s = sub.add_parser('selftest', help='环境自检：随机盘对拍 + 解读检查')
    s.add_argument('--n', type=int, default=50)
    s.add_argument('--seed', type=int, default=1)
    s.set_defaults(func=cmd_selftest)
    a = p.parse_args()
    if getattr(a, 'cmd', '') == 'hours' and not (a.around or a.all):
        p.error('hours 需要 --around HH:MM 或 --all')
    a.func(a)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:  # 输出被 head 之类截断时安静退出
        sys.stderr.close()
    except ValueError as e:  # 输入不合法：日期不存在、农历没有这个闰月、性别写错等
        sys.exit(f'输入有误：{e}')
