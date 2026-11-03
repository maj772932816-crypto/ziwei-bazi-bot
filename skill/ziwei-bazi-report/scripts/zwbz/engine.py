"""把输入整理成一份完整的「事实」：时间处理、八字、紫微、逐年表、流月、边界问题、内部核对与整体状态。"""
import datetime as dt

from . import __version__, bazi, ziwei
from .astro import from_bj, jie_around, to_bj
from .flow import month_rows, year_rows
from .lunar import lunar_to_solar, solar_to_lunar
from .place import china_dst, find_city, true_solar

BR = bazi.BRANCHES


def _hour_boundary_minutes(t: dt.datetime) -> tuple:
    """离最近的时辰交界（奇数整点）有多少分钟，以及交界另一侧的时辰。"""
    m = t.hour * 60 + t.minute + t.second / 60
    best = None
    for h in range(1, 24, 2):
        for edge in (h * 60, h * 60 - 1440, h * 60 + 1440):
            d = abs(m - edge)
            if best is None or d < best[0]:
                best = (d, edge)
    d, edge = best
    other = t + dt.timedelta(minutes=(edge - m) + (1 if m < edge else -1))
    return round(d, 1), BR[bazi.hour_branch_index(other)]


def _issue(code, level, message, question=''):
    """level：confirm＝出报告前要问用户；info＝写进报告即可；stop＝不能继续。"""
    return {'code': code, 'level': level, 'message': message, 'question': question}


def parse_gender(g: str) -> str:
    g = {'男': 'male', '女': 'female', 'm': 'male', 'f': 'female', '乾': 'male', '坤': 'female'}.get(g, g)
    if g not in ('male', 'female'):
        raise ValueError('性别请填 男 或 女')
    return g


def build(date: str, time: str, gender: str, *, calendar: str = 'solar', leap: bool = False,
          city: str = '', lon: float = None, tz: float = 8.0, solar_time: bool = True,
          dst_adjust: bool = False, zi_sect: str = 'next', leap_policy: str = 'split',
          years_from: int = None, years_count: int = 10, months_year: int = None, name: str = '') -> dict:
    gender = parse_gender(gender)
    issues = []
    y, m, d = (int(x) for x in date.replace('/', '-').replace('.', '-').split('-'))
    if calendar == 'lunar':
        sd = lunar_to_solar(y, m, d, leap)
        issues.append(_issue('LUNAR_INPUT', 'info', f'输入为农历{y}年{"闰" if leap else ""}{m}月{d}日，换算公历 {sd.isoformat()}'))
    else:
        sd = dt.date(y, m, d)
    hour_known = time not in ('', 'unknown', '未知', None)
    hh, mm = (int(x) for x in time.split(':')) if hour_known else (12, 0)
    clock = dt.datetime(sd.year, sd.month, sd.day, hh, mm)

    # 出生地
    place = None
    if lon is not None:
        place = {'province': '', 'city': city or '自定义', 'longitude': float(lon)}
    elif city:
        hits = find_city(city)
        if hits:
            place = {'province': hits[0][0], 'city': hits[0][1], 'longitude': hits[0][2]}
            if len(hits) > 1:
                issues.append(_issue('CITY_AMBIGUOUS', 'info', '同名地点有多个：' + '、'.join(f'{p}{c}（东经{lo}°）' for p, c, lo in hits[:5])
                                     + f'，已取 {hits[0][0]}{hits[0][1]}；如果不对，请用省份加城市重排'))
        else:
            issues.append(_issue('CITY_NOT_FOUND', 'confirm', f'没找到「{city}」的经度，没有做真太阳时校正',
                                 f'「{city}」属于哪个省、哪个地级市？或者告诉我它附近的大城市。'))
    elif hour_known:
        issues.append(_issue('NO_PLACE', 'info', '没有出生地，按钟表时间排盘，未做真太阳时校正'))

    # 夏令时
    dst = china_dst(sd) if tz == 8 else None
    if dst and hour_known and dst_adjust:
        clock -= dt.timedelta(hours=1)
        issues.append(_issue('DST_ADJUSTED', 'info', f'出生日期在中国大陆夏令时期间（{dst[0]}–{dst[1]}），已按「记录的是当时的钟表时间」减去 1 小时'))

    instant = from_bj(clock - dt.timedelta(hours=tz - 8))
    solar = None
    basis = clock
    if place and solar_time and hour_known:
        solar = true_solar(clock, place['longitude'], tz)
        basis = solar['time']
    basis_label = '真太阳时' if solar else '钟表时间'

    if dst and hour_known and not dst_adjust:
        alt_clock = clock - dt.timedelta(hours=1)
        alt = true_solar(alt_clock, place['longitude'], tz)['time'] if (place and solar_time) else alt_clock
        hb, hb_alt = bazi.hour_branch_index(basis), bazi.hour_branch_index(alt)
        shifted = lambda t: t.date() + dt.timedelta(days=1 if t.hour == 23 else 0)  # noqa: E731
        msg = f'出生日期在中国大陆夏令时期间（{dst[0]}–{dst[1]}），当时钟表拨快 1 小时'
        if hb == hb_alt and shifted(basis) == shifted(alt):
            issues.append(_issue('DST_SAME', 'info', msg + f'；即使记录的是当时的钟表时间（实际早 1 小时），也仍是{BR[hb]}时，盘不变'))
        else:
            issues.append(_issue('DST_CHANGES', 'confirm', msg + f'；如果记录的是当时的钟表时间，实际早 1 小时，会从{BR[hb]}时变成{BR[hb_alt]}时，八字时柱和整张紫微盘都会不同',
                                 '你的出生时间是出生证明上的时间吗？那时正好是夏令时，钟表拨快了 1 小时。如果是当时的钟表时间，我按减 1 小时来排。'))

    # 八字
    bz = bazi.compute(basis, gender, instant, zi_sect=zi_sect, hour_known=hour_known)

    # 紫微：晚子时（23 点后）按次日子时排
    zw = None
    lunar_basis = basis.date()
    hour_idx = bazi.hour_branch_index(basis) if hour_known else None
    if hour_known and basis.hour == 23:
        lunar_basis += dt.timedelta(days=1)
        issues.append(_issue('LATE_ZI', 'info', '出生在 23 点后（晚子时）：紫微按次日子时排盘；八字按「'
                             + ('23 点换日' if zi_sect == 'next' else '晚子时日柱算当天') + '」'))
    L = solar_to_lunar(lunar_basis)
    if hour_known:
        mu = L.month
        if L.leap:
            if leap_policy == 'next' or (leap_policy == 'split' and L.day > 15):
                mu = L.month % 12 + 1
            issues.append(_issue('LEAP_MONTH', 'info', f'农历闰{L.month}月出生，按「'
                                 + {'split': '前十五天算本月、后半月算下月', 'next': '闰月算下月', 'current': '闰月算本月'}[leap_policy]
                                 + f'」取第 {mu} 月排紫微'))
        ys, yb = (L.year - 4) % 10, (L.year - 4) % 12
        zw = ziwei.chart(mu, L.day, hour_idx, ys, yb, gender == 'male')
    else:
        issues.append(_issue('NO_TIME', 'info', '没有出生时间：只排八字年、月、日三柱，不排时柱和紫微盘（紫微必须有时辰）'))

    # 边界
    if hour_known:
        dmin, other = _hour_boundary_minutes(basis)
        if dmin < 15:
            issues.append(_issue('HOUR_BOUNDARY', 'confirm',
                                 f'出生时间（{basis_label} {basis:%H:%M}）离时辰交界只有 {dmin} 分钟，另一侧是{other}时；记录差几分钟，时柱和整张紫微盘都会变',
                                 f'出生时间是出生证明上精确到分钟的吗？如果只是大概，我可以把{BR[hour_idx]}时和{other}时两张盘都排出来对照。'))
        if solar and bazi.hour_branch_index(clock) != hour_idx:
            issues.append(_issue('SOLAR_HOUR_SHIFT', 'info', f'真太阳时校正后时辰从{BR[bazi.hour_branch_index(clock)]}时变为{BR[hour_idx]}时'))
    j = jie_around(instant)
    for nm, t in (j['prev'], j['next']):
        hours = abs(float(t) - float(instant)) * 24
        if hours < 3:
            issues.append(_issue('JIE_BOUNDARY', 'confirm',
                                 f'出生时刻离{nm}（{to_bj(t):%Y-%m-%d %H:%M}）只有 {hours:.1f} 小时，月柱{"和年柱" if nm == "立春" else ""}在交界附近',
                                 '出生时间准确到分钟吗？离节气交界很近，差一点月柱就不同。'))
    if bz['pillars'][0] != L.year_gz:
        issues.append(_issue('YEAR_DIFF', 'info', f'八字年柱按立春换年为{bz["pillars"][0]}，紫微按正月初一换年为{L.year_gz}，两者不同属正常'))

    facts = {
        'tool': 'zwbz', 'version': __version__,
        'input': {
            'name': name, 'gender': gender, 'calendar': calendar, 'date_input': date, 'time_input': time,
            'solar_date': sd.isoformat(), 'clock': clock.strftime('%Y-%m-%d %H:%M') if hour_known else None,
            'tz': tz, 'place': place, 'birth_year_for_age': L.year,
            'basis': basis_label if hour_known else '无时辰', 'basis_time': basis.strftime('%Y-%m-%d %H:%M') if hour_known else None,
            'true_solar': ({'longitude_minutes': solar['longitude_minutes'], 'eot_minutes': solar['eot_minutes']} if solar else None),
            'zi_sect': zi_sect, 'leap_policy': leap_policy, 'dst_adjust': dst_adjust,
        },
        'lunar': {'year': L.year, 'month': L.month, 'day': L.day, 'leap': L.leap, 'text': L.text(),
                  'from_date': lunar_basis.isoformat()},
        'bazi': bz, 'ziwei': zw, 'issues': issues, 'checks': [],
    }
    if hour_known:
        facts['dataset_key'] = f'{lunar_basis.isoformat()}-{hour_idx}-{gender}'
    start = years_from or dt.date.today().year
    facts['years'] = year_rows(facts, start, years_count) if hour_known else []
    if months_year and hour_known:
        facts['months'] = month_rows(facts, months_year)
    facts['checks'].extend(self_checks(facts))
    refresh(facts)
    return facts


def refresh(facts: dict) -> dict:
    """由 issues 和 checks 重新算出 warnings、notes 和整体状态。"""
    issues = facts.get('issues', [])
    facts['warnings'] = [i['message'] for i in issues if i['level'] == 'confirm']
    facts['notes'] = [i['message'] for i in issues if i['level'] == 'info']
    stop = [c for c in facts['checks'] if c['status'] == 'fail']
    env = [c for c in facts['checks'] if c['status'] == 'warn' and c['item'] == '交叉核对']
    confirm = [i for i in issues if i['level'] == 'confirm']
    if stop or env:
        status = 'stop'
        nxt = ('核对不一致：不要出报告，把不一致的项目告诉用户。' if stop else
               '交叉核对没有运行：先执行 scripts/install.sh 修好环境，再重新排盘。')
    elif confirm:
        status = 'confirm'
        nxt = '先把 questions 里的问题问用户，确认后按回答加参数重新排盘（比如 --dst-adjust、换时间、换城市）。'
    else:
        status = 'ok'
        nxt = '可以写分析：读 brief，按写作规则写 narrative.json，lint 通过后 render。'
    facts['status'] = {'status': status, 'next': nxt,
                       'reasons': [c['item'] + '：' + c['result'] for c in stop + env] + [i['message'] for i in confirm],
                       'questions': [i['question'] for i in confirm if i['question']]}
    return facts


def self_checks(facts: dict) -> list:
    """不依赖外部库的内部一致性核对。"""
    out = []
    p = facts['bazi']['pillars']
    out.append({'item': '日柱（儒略日推算）', 'status': 'ok', 'result': p[2],
                'method': '儒略日序号模 60，以 2000-01-01 戊午日校准'})
    if facts['ziwei']:
        zw = facts['ziwei']
        majors = sum(1 for pl in zw['palaces'] for s in pl['stars'] if s['type'] == 'major')
        minors = sum(1 for pl in zw['palaces'] for s in pl['stars'] if s['type'] == 'minor')
        ok = majors == 14 and minors == 14
        out.append({'item': '紫微星曜完整性', 'status': 'ok' if ok else 'fail',
                    'result': f'主星 {majors}/14，六吉六煞禄马 {minors}/14', 'method': '每颗星恰好落一宫'})
        hua = [s for pl in zw['palaces'] for s in pl['stars'] if 'hua' in s]
        out.append({'item': '生年四化', 'status': 'ok' if len(hua) == 4 else 'fail',
                    'result': '、'.join(f"{s['name']}化{s['hua']}" for s in hua), 'method': f"按年干{zw['year_gz'][0]}查四化表"})
    return out
