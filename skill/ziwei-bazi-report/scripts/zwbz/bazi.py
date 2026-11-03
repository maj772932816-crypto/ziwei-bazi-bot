"""八字：四柱、十神、藏干、十二长生、纳音、空亡、神煞、五行计分、大运起运、干支作用关系。"""
import datetime as dt

import ephem

from .astro import JIE, jie_around, lichun, from_bj, to_bj

STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
WX = '木火土金水'
STEM_WX = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
BRANCH_WX = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]
HIDDEN = {  # 本气、中气、余气
    '子': '癸', '丑': '己癸辛', '寅': '甲丙戊', '卯': '乙', '辰': '戊乙癸', '巳': '丙庚戊',
    '午': '丁己', '未': '己丁乙', '申': '庚壬戊', '酉': '辛', '戌': '戊辛丁', '亥': '壬甲',
}
HIDDEN_W = [1.0, 0.5, 0.3]
STAGES = '长生 沐浴 冠带 临官 帝旺 衰 病 死 墓 绝 胎 养'.split()
CHANGSHENG = {'甲': 11, '丙': 2, '戊': 2, '庚': 5, '壬': 8, '乙': 6, '丁': 9, '己': 9, '辛': 0, '癸': 3}
NAYIN = ['海中金', '炉中火', '大林木', '路旁土', '剑锋金', '山头火', '涧下水', '城头土', '白蜡金', '杨柳木',
         '泉中水', '屋上土', '霹雳火', '松柏木', '长流水', '沙中金', '山下火', '平地木', '壁上土', '金箔金',
         '覆灯火', '天河水', '大驿土', '钗钏金', '桑柘木', '大溪水', '沙中土', '天上火', '石榴木', '大海水']

GAN_HE = {frozenset(p): wx for p, wx in [('甲己', '土'), ('乙庚', '金'), ('丙辛', '水'), ('丁壬', '木'), ('戊癸', '火')]}
GAN_CHONG = [frozenset(p) for p in ['甲庚', '乙辛', '丙壬', '丁癸']]
LIU_HE = {frozenset(p): wx for p, wx in [('子丑', '土'), ('寅亥', '木'), ('卯戌', '火'), ('辰酉', '金'), ('巳申', '水'), ('午未', '土')]}
LIU_CHONG = [frozenset(p) for p in ['子午', '丑未', '寅申', '卯酉', '辰戌', '巳亥']]
LIU_HAI = [frozenset(p) for p in ['子未', '丑午', '寅巳', '卯辰', '申亥', '酉戌']]
SAN_HE = {'申子辰': '水', '亥卯未': '木', '寅午戌': '火', '巳酉丑': '金'}
XING_PAIRS = [frozenset(p) for p in ['寅巳', '巳申', '寅申', '丑戌', '戌未', '丑未', '子卯']]
SAN_XING = ['寅巳申', '丑戌未']
ZI_XING = set('辰午酉亥')


def gz(i: int) -> str:
    return STEMS[i % 10] + BRANCHES[i % 12]


def gz_index(s: str) -> int:
    a, b = STEMS.index(s[0]), BRANCHES.index(s[1])
    return next(i for i in range(60) if i % 10 == a and i % 12 == b)


def ten_god(day_stem: str, other: str) -> str:
    d, o = STEMS.index(day_stem), STEMS.index(other)
    de, oe = STEM_WX[d], STEM_WX[o]
    same = (d % 2) == (o % 2)
    if de == oe:
        return '比肩' if same else '劫财'
    if (de + 1) % 5 == oe:
        return '食神' if same else '伤官'
    if (de + 2) % 5 == oe:
        return '偏财' if same else '正财'
    if (oe + 2) % 5 == de:
        return '七杀' if same else '正官'
    return '偏印' if same else '正印'


def stage(stem: str, branch: str) -> str:
    s, b = CHANGSHENG[stem], BRANCHES.index(branch)
    return STAGES[(b - s) % 12 if STEMS.index(stem) % 2 == 0 else (s - b) % 12]


def kongwang(pillar: str) -> str:
    i = gz_index(pillar)
    head = i - i % 10
    return BRANCHES[(head + 10) % 12] + BRANCHES[(head + 11) % 12]


def jdn(d: dt.date) -> int:
    return d.toordinal() + 1721425


def day_pillar(d: dt.date) -> str:
    return gz((jdn(d) + 49) % 60)


def hour_pillar(day_stem: str, hour_branch_idx: int) -> str:
    zi_stem = (STEMS.index(day_stem) % 5) * 2
    return STEMS[(zi_stem + hour_branch_idx) % 10] + BRANCHES[hour_branch_idx]


def hour_branch_index(t: dt.datetime) -> int:
    return ((t.hour + 1) // 2) % 12


def shensha(day_stem: str, year_branch: str, day_branch: str) -> dict:
    """常用神煞所在地支。"""
    tianyi = {'甲': '丑未', '戊': '丑未', '乙': '子申', '己': '子申', '丙': '亥酉', '丁': '亥酉',
              '壬': '卯巳', '癸': '卯巳', '庚': '午寅', '辛': '午寅'}[day_stem]
    wenchang = dict(zip(STEMS, '巳午申酉申酉亥子寅卯'))[day_stem]
    lu = dict(zip(STEMS, '寅卯巳午巳午申酉亥子'))[day_stem]
    yangren = {'甲': '卯', '丙': '午', '戊': '午', '庚': '酉', '壬': '子'}.get(day_stem, '')
    def sanhe_group(b):
        for g in SAN_HE:
            if b in g:
                return g
    MA = {'申子辰': '寅', '寅午戌': '申', '巳酉丑': '亥', '亥卯未': '巳'}
    TAO = {'申子辰': '酉', '寅午戌': '卯', '巳酉丑': '午', '亥卯未': '子'}
    HUA = {'申子辰': '辰', '寅午戌': '戌', '巳酉丑': '丑', '亥卯未': '未'}
    yb = BRANCHES.index(year_branch)
    hongluan = BRANCHES[(3 - yb) % 12]
    return {
        '天乙贵人': tianyi, '文昌贵人': wenchang, '禄神': lu, '羊刃': yangren,
        '驿马': ''.join(sorted({MA[sanhe_group(year_branch)], MA[sanhe_group(day_branch)]})),
        '桃花': ''.join(sorted({TAO[sanhe_group(year_branch)], TAO[sanhe_group(day_branch)]})),
        '华盖': ''.join(sorted({HUA[sanhe_group(year_branch)], HUA[sanhe_group(day_branch)]})),
        '红鸾': hongluan, '天喜': BRANCHES[(BRANCHES.index(hongluan) + 6) % 12],
    }


def relations(stems: dict, branches: dict) -> list:
    """一组带位置标签的天干、地支之间的作用关系（合、冲、刑、害、三合、半合、自刑）。"""
    out = []
    sk = list(stems.items())
    for i in range(len(sk)):
        for j in range(i + 1, len(sk)):
            (pa, a), (pb, b) = sk[i], sk[j]
            pair = frozenset(a + b)
            if pair in GAN_HE:
                out.append(f'{pa}干{a}与{pb}干{b}相合（化{GAN_HE[pair]}）')
            if pair in GAN_CHONG:
                out.append(f'{pa}干{a}与{pb}干{b}相冲')
    bk = list(branches.items())
    for i in range(len(bk)):
        for j in range(i + 1, len(bk)):
            (pa, a), (pb, b) = bk[i], bk[j]
            pair = frozenset(a + b)
            if a == b:
                out.append(f'{pa}支与{pb}支同为{a}（伏吟）' + ('，自刑' if a in ZI_XING else ''))
                continue
            if pair in LIU_HE:
                out.append(f'{pa}支{a}与{pb}支{b}六合（{LIU_HE[pair]}）')
            if pair in LIU_CHONG:
                out.append(f'{pa}支{a}与{pb}支{b}相冲')
            if pair in XING_PAIRS:
                out.append(f'{pa}支{a}与{pb}支{b}相刑')
            if pair in LIU_HAI:
                out.append(f'{pa}支{a}与{pb}支{b}相害')
    present = set(branches.values())
    for g, w in SAN_HE.items():
        have = present & set(g)
        if len(have) == 3:
            out.append(f'{g}三合{w}局')
        elif len(have) == 2:
            mid = g[1]
            if mid in have:
                out.append(f'{"".join(c for c in g if c in have)}半合{w}局')
            else:
                out.append(f'{g[0]}{g[2]}拱{mid}（遇{mid}成{w}局）')
    for g in SAN_XING:
        if set(g) <= present:
            out.append(f'{g}三刑俱全')
    return out


def wuxing_score(pillars: list, month_double: bool = False) -> dict:
    """五行计分：天干 1，地支本气 1、中气 0.5、余气 0.3；month_double 时月令本气再加 1。"""
    sc = {w: 0.0 for w in WX}
    for k, p in enumerate(pillars):
        sc[WX[STEM_WX[STEMS.index(p[0])]]] += 1
        for w, h in zip(HIDDEN_W, HIDDEN[p[1]]):
            sc[WX[STEM_WX[STEMS.index(h)]]] += w
        if month_double and k == 1:
            sc[WX[STEM_WX[STEMS.index(HIDDEN[p[1]][0])]]] += 1
    return {w: round(v, 2) for w, v in sc.items()}


def strength(day_stem: str, pillars: list) -> dict:
    de = STEM_WX[STEMS.index(day_stem)]
    self_wx = {WX[de], WX[(de + 4) % 5]}  # 比劫 + 印
    plain = wuxing_score(pillars)
    weighted = wuxing_score(pillars, month_double=True)
    def split(sc):
        s = sum(v for w, v in sc.items() if w in self_wx)
        return round(s, 2), round(sum(sc.values()) - s, 2)
    s1, o1 = split(plain)
    s2, o2 = split(weighted)
    month_main = HIDDEN[pillars[1][1]][0]
    deling = WX[STEM_WX[STEMS.index(month_main)]] in self_wx
    ratio = s2 / o2 if o2 else 9
    label = '偏旺' if ratio > 1.25 else '偏弱' if ratio < 0.8 else ('中和略偏旺' if ratio >= 1 else '中和略偏弱')
    season = '冬' if pillars[1][1] in '亥子丑' else '夏' if pillars[1][1] in '巳午未' else '春' if pillars[1][1] in '寅卯辰' else '秋'
    tiaohou = {'冬': '冬月寒，喜火调候', '夏': '夏月燥热，喜水调候'}.get(season, '春秋气候平和，调候需求不强')
    return {'score': plain, 'score_month_weighted': weighted, 'self_elements': sorted(self_wx),
            'self_vs_other': [s1, o1], 'self_vs_other_month_weighted': [s2, o2], 'de_ling': deling,
            'label': label, 'season': season, 'tiaohou': tiaohou,
            'method': '天干 1，地支本气 1、中气 0.5、余气 0.3；加权版月令本气再加 1。标签按加权比值：>1.25 偏旺，<0.8 偏弱，其余中和'}


def compute(local: dt.datetime, gender: str, instant_utc: ephem.Date, zi_sect: str = 'next',
            hour_known: bool = True) -> dict:
    """local：用来定日柱、时柱的当地时间（已做真太阳时校正时即为真太阳时）；instant_utc：出生瞬间，用来比节气。
    zi_sect='next'：23 点起算次日（子初换日）；'same'：晚子时日柱仍算当天，时干按次日起。"""
    y = local.year if instant_utc >= lichun(local.year) else local.year - 1
    year_p = gz((y - 4) % 60)
    jie = jie_around(instant_utc)
    k = jie['month_index']
    yin_stem = ((STEMS.index(year_p[0]) % 5) * 2 + 2) % 10
    month_p = STEMS[(yin_stem + k) % 10] + BRANCHES[(2 + k) % 12]
    day = local.date()
    late_zi = hour_known and local.hour == 23
    if late_zi and zi_sect == 'next':
        day = day + dt.timedelta(days=1)
    day_p = day_pillar(day)
    pillars = [year_p, month_p, day_p]
    if hour_known:
        hb = hour_branch_index(local)
        stem_day = day_pillar(day + dt.timedelta(days=1))[0] if (late_zi and zi_sect == 'same') else day_p[0]
        pillars.append(hour_pillar(stem_day, hb))
    dm = day_p[0]
    labels = ['年', '月', '日', '时']
    detail = []
    for i, p in enumerate(pillars):
        detail.append({
            'pos': labels[i], 'pillar': p,
            'stem_god': '日主' if i == 2 else ten_god(dm, p[0]),
            'hidden': [{'stem': h, 'god': ten_god(dm, h)} for h in HIDDEN[p[1]]],
            'stage': stage(dm, p[1]), 'self_stage': stage(p[0], p[1]),
            'nayin': NAYIN[gz_index(p) // 2],
        })
    # 大运
    yang_year = STEMS.index(year_p[0]) % 2 == 0
    forward = yang_year == (gender == 'male')
    prev_name, prev_t = jie['prev']
    next_name, next_t = jie['next']
    delta = (next_t - instant_utc) if forward else (instant_utc - prev_t)
    years = delta / 3.0
    birth_bj = to_bj(instant_utc)
    start = birth_bj + dt.timedelta(days=delta * 365.2425 / 3.0)
    mi = gz_index(month_p)
    dayun = []
    for i in range(1, 10):
        g = gz((mi + i) % 60 if forward else (mi - i) % 60)
        s = start + dt.timedelta(days=3652.425 * (i - 1))
        dayun.append({'pillar': g, 'start': s.strftime('%Y-%m-%d'), 'start_year': s.year,
                      'start_age': round((s - birth_bj).days / 365.2425, 1), 'start_age_xu': s.year - birth_bj.year + 1,
                      'stem_god': ten_god(dm, g[0]), 'branch_god': ten_god(dm, HIDDEN[g[1]][0])})
    stems = {labels[i]: p[0] for i, p in enumerate(pillars)}
    branches = {labels[i]: p[1] for i, p in enumerate(pillars)}
    base = set(relations(stems, branches))
    for d in dayun:
        rel = relations({**stems, '大运': d['pillar'][0]}, {**branches, '大运': d['pillar'][1]})
        d['relations'] = [r for r in rel if r not in base]
    return {
        'pillars': pillars, 'detail': detail, 'day_master': dm,
        'kongwang': {'日柱旬空': kongwang(day_p), '年柱旬空': kongwang(year_p)},
        'shensha': shensha(dm, year_p[1], day_p[1]),
        'relations': relations(stems, branches),
        'strength': strength(dm, pillars) if hour_known else None,
        'jie': {'prev': [prev_name, to_bj(prev_t).strftime('%Y-%m-%d %H:%M')],
                'next': [next_name, to_bj(next_t).strftime('%Y-%m-%d %H:%M')]},
        'yun': {'forward': forward, 'days_to_jie': round(delta, 3), 'start_age': round(years, 2),
                'start_date': start.strftime('%Y-%m-%d'), 'rule': '三天折一年，按时长比例折算'},
        'dayun': dayun, 'zi_sect': zi_sect, 'late_zi': late_zi,
    }
