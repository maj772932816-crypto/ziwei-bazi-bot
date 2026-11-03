"""出生地经度、真太阳时、中国大陆夏令时。"""
import datetime as dt
import json
import math
import os

_D = os.path.join(os.path.dirname(__file__), 'data')
_CITIES = json.load(open(os.path.join(_D, 'cities.json'), encoding='utf-8'))['provinces']
_DST = json.load(open(os.path.join(_D, 'dst_cn.json'), encoding='utf-8'))['rows']
_SUFFIX = ('特别行政区', '维吾尔自治区', '壮族自治区', '回族自治区', '自治区', '自治州', '地区', '省', '市', '县', '区', '盟')


def _norm(s: str) -> str:
    s = s.strip()
    for suf in _SUFFIX:
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


def find_city(name: str):
    """按城市名找经度。返回 (省, 市, 经度) 或 None；同名时返回第一个，并在 candidates 里列出全部。"""
    want = _norm(name)
    hits = []
    for prov, cities in _CITIES.items():
        for city, lon in cities.items():
            if _norm(city) == want or (want.startswith(_norm(prov)) and _norm(want[len(_norm(prov)):]) == _norm(city)):
                hits.append((prov, city, lon))
    if not hits:
        for prov, cities in _CITIES.items():
            for city, lon in cities.items():
                if want and (want in city or city in want):
                    hits.append((prov, city, lon))
    return hits


def equation_of_time(t: dt.datetime) -> float:
    """NOAA 均时差近似式（分钟），与开源排盘引擎同一公式；正值表示真太阳时快于平太阳时。"""
    days = 366 if (t.year % 4 == 0 and (t.year % 100 != 0 or t.year % 400 == 0)) else 365
    doy = t.timetuple().tm_yday
    g = 2 * math.pi / days * (doy - 1 + (t.hour + t.minute / 60 - 12) / 24)
    return 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))


def true_solar(clock: dt.datetime, lon: float, tz_hours: float = 8.0) -> dict:
    lon_fix = (lon - 15 * tz_hours) * 4
    eot = equation_of_time(clock)
    t = clock + dt.timedelta(minutes=lon_fix + eot)
    return {'time': t, 'longitude_minutes': round(lon_fix, 1), 'eot_minutes': round(eot, 1)}


def china_dst(d: dt.date):
    """若该日处于中国大陆夏令时期间，返回 (起, 止) 文本，否则 None。按日期判定，起止日都含。"""
    for y, m1, d1, m2, d2 in _DST:
        if d.year != y:
            continue
        inside = (m1 < d.month < m2) or (d.month == m1 and d.day >= d1) or (d.month == m2 and d.day <= d2)
        if inside:
            return f'{y}年{m1}月{d1}日', f'{y}年{m2}月{d2}日'
    return None
