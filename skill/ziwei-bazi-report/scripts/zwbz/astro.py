"""天文计算：太阳视黄经、节气时刻、朔日。

依赖 ephem（pip install ephem）。内部时刻一律用 UTC 的 ephem.Date，北京时间 = UTC + 8 小时。
太阳视黄经用视地心坐标（含光行差与章动），节气时刻与 lunar-javascript 节气表相差不到 1 分钟。
"""
import datetime as dt
import math

import ephem

BJ = dt.timedelta(hours=8)
DEG_PER_DAY = 0.98564736

# 十二「节」（定月柱），从寅月的立春起；十二「中气」（定农历月、闰月）
JIE = [(315, '立春'), (345, '惊蛰'), (15, '清明'), (45, '立夏'), (75, '芒种'), (105, '小暑'),
       (135, '立秋'), (165, '白露'), (195, '寒露'), (225, '立冬'), (255, '大雪'), (285, '小寒')]
ZHONGQI = [(330, '雨水'), (0, '春分'), (30, '谷雨'), (60, '小满'), (90, '夏至'), (120, '大暑'),
           (150, '处暑'), (180, '秋分'), (210, '霜降'), (240, '小雪'), (270, '冬至'), (300, '大寒')]


def sun_lon(d) -> float:
    """太阳视黄经（度，0–360），相对当日春分点。"""
    s = ephem.Sun(ephem.Date(d))
    eq = ephem.Equatorial(s.g_ra, s.g_dec, epoch=ephem.Date(d))
    return math.degrees(ephem.Ecliptic(eq).lon) % 360


def term_time(deg: float, guess) -> ephem.Date:
    """太阳视黄经到达 deg 的时刻（UTC），从 guess 附近牛顿迭代。"""
    t = float(ephem.Date(guess))
    for _ in range(12):
        diff = ((sun_lon(t) - deg + 180) % 360) - 180
        t -= diff / DEG_PER_DAY
        if abs(diff) < 1e-7:
            break
    return ephem.Date(t)


def to_bj(d) -> dt.datetime:
    return ephem.Date(d).datetime() + BJ


def from_bj(x: dt.datetime) -> ephem.Date:
    return ephem.Date(x - BJ)


def lichun(year: int) -> ephem.Date:
    return term_time(315, ephem.Date(f'{year}/2/4'))


def jie_around(t) -> dict:
    """t 所在节气月：月序（0=寅月 … 11=丑月）、上一个节与下一个节的名称和时刻。"""
    lam = sun_lon(t)
    k = int(((lam - 315) % 360) // 30)
    prev_deg, prev_name = JIE[k]
    next_deg, next_name = JIE[(k + 1) % 12]
    prev_t = term_time(prev_deg, float(t) - ((lam - prev_deg) % 360) / DEG_PER_DAY)
    next_t = term_time(next_deg, float(t) + ((next_deg - lam) % 360) / DEG_PER_DAY)
    return {'month_index': k, 'prev': (prev_name, prev_t), 'next': (next_name, next_t)}


def new_moon_dates(start: dt.date, end: dt.date) -> list:
    """北京时间日期计的朔日列表（覆盖 start 之前一个朔到 end 之后一个朔）。"""
    t = ephem.previous_new_moon(from_bj(dt.datetime(start.year, start.month, start.day)))
    out = []
    while True:
        d = to_bj(t).date()
        out.append(d)
        if d > end:
            break
        t = ephem.next_new_moon(ephem.Date(t + 1))
    return out
