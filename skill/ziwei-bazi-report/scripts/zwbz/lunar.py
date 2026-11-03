"""农历换算（公历 ⇄ 农历），按现行规则用天文算法独立推算。

规则：朔日所在的北京时间日期为初一；冬至所在的月为十一月；两个冬至月之间有 13 个月时，
其中第一个不含中气的月为闰月（中气按北京时间日期归月，与朔同日的中气属于新月份）。
"""
import datetime as dt
from functools import lru_cache
from typing import NamedTuple

import ephem

from .astro import new_moon_dates, term_time, to_bj

STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
MONTH_NAMES = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊']
DAY_NAMES = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
             '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
             '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十']


class LunarDate(NamedTuple):
    year: int          # 农历年（以正月初一换年）
    month: int         # 1–12
    day: int           # 1–30
    leap: bool         # 是否闰月
    month_days: int    # 本月天数（29/30）

    @property
    def year_gz(self) -> str:
        i = (self.year - 4) % 60
        return STEMS[i % 10] + BRANCHES[i % 12]

    def text(self) -> str:
        return f"{self.year_gz}年{'闰' if self.leap else ''}{MONTH_NAMES[self.month - 1]}月{DAY_NAMES[self.day - 1]}"


@lru_cache(maxsize=256)
def _months(y: int):
    """y 年冬至所在月（十一月）起，到 y+1 年冬至所在月之前的各月：[(初一日期, 月数, 是否闰月)]，以及终止日。"""
    ws0 = term_time(270, ephem.Date(f'{y}/12/21'))
    ws1 = term_time(270, ephem.Date(f'{y + 1}/12/21'))
    d0, d1 = to_bj(ws0).date(), to_bj(ws1).date()
    nms = new_moon_dates(d0 - dt.timedelta(days=40), d1 + dt.timedelta(days=40))
    s0 = max(x for x in nms if x <= d0)
    s1 = max(x for x in nms if x <= d1)
    starts = [x for x in nms if s0 <= x < s1]
    zq = [to_bj(term_time((270 + 30 * k) % 360, ephem.Date(float(ws0) + 30.436875 * k))).date() for k in range(13)]
    ends = starts[1:] + [s1]
    has_zq = [any(a <= z < b for z in zq) for a, b in zip(starts, ends)]
    out, num, leap_done = [], 11, False
    for i, st in enumerate(starts):
        if i == 0:
            out.append((st, 11, False))
            continue
        if len(starts) == 13 and not leap_done and not has_zq[i]:
            out.append((st, num, True))
            leap_done = True
            continue
        num = num % 12 + 1
        out.append((st, num, False))
    return tuple(out), s1


def _entries(y: int):
    """带农历年号的月份条目：[(初一, 农历年, 月, 闰, 天数)]。"""
    months, end = _months(y)
    first_zheng = next(i for i, (_, n, lp) in enumerate(months) if n == 1 and not lp)
    res = []
    for i, (st, n, lp) in enumerate(months):
        nxt = months[i + 1][0] if i + 1 < len(months) else end
        res.append((st, y if i < first_zheng else y + 1, n, lp, (nxt - st).days))
    return res


def solar_to_lunar(d: dt.date) -> LunarDate:
    for y in (d.year - 1, d.year):
        for st, ly, n, lp, days in _entries(y):
            if st <= d < st + dt.timedelta(days=days):
                return LunarDate(ly, n, (d - st).days + 1, lp, days)
    raise ValueError(f'无法换算农历：{d}')


def lunar_to_solar(year: int, month: int, day: int, leap: bool = False) -> dt.date:
    for y in (year - 1, year):
        for st, ly, n, lp, days in _entries(y):
            if ly == year and n == month and lp == leap:
                if not 1 <= day <= days:
                    raise ValueError(f'农历{year}年{"闰" if leap else ""}{month}月只有 {days} 天')
                return st + dt.timedelta(days=day - 1)
    raise ValueError(f'农历{year}年没有{"闰" if leap else ""}{month}月')
