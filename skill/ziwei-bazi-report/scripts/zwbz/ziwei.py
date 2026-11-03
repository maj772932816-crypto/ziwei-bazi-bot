"""紫微斗数安星（三合派通行口径），独立实现，供与 iztro 交叉核对。

输入用「排盘口径」的农历：农历年干支（正月初一换年）、月（已按闰月规则折算）、日、时辰序号（子=0）。
亮度用《紫微斗数全书》表（主星），四化用通行表（庚：阳武阴同；壬：梁紫左武）。
"""
import json
import os

ST, BR = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
PALACES = ['命宫', '兄弟', '夫妻', '子女', '财帛', '疾厄', '迁移', '仆役', '官禄', '田宅', '福德', '父母']
NAYIN_WX = ['金', '火', '木', '土', '金', '火', '水', '土', '金', '木', '水', '土', '火', '木', '水',
            '金', '火', '木', '土', '金', '火', '水', '土', '金', '木', '水', '土', '火', '木', '水']
JU = {'水': 2, '木': 3, '金': 4, '土': 5, '火': 6}
JU_NAME = {2: '水二局', 3: '木三局', 4: '金四局', 5: '土五局', 6: '火六局'}
SIHUA = {'甲': '廉贞 破军 武曲 太阳', '乙': '天机 天梁 紫微 太阴', '丙': '天同 天机 文昌 廉贞', '丁': '太阴 天同 天机 巨门',
         '戊': '贪狼 太阴 右弼 天机', '己': '武曲 贪狼 天梁 文曲', '庚': '太阳 武曲 太阴 天同', '辛': '巨门 太阳 文曲 文昌',
         '壬': '天梁 紫微 左辅 武曲', '癸': '破军 巨门 太阴 贪狼'}
MAJOR = ['紫微', '天机', '太阳', '武曲', '天同', '廉贞', '天府', '太阴', '贪狼', '巨门', '天相', '天梁', '七杀', '破军']
MINOR = ['左辅', '右弼', '文昌', '文曲', '天魁', '天钺', '禄存', '天马', '擎羊', '陀罗', '火星', '铃星', '地空', '地劫']
SHA = {'擎羊', '陀罗', '火星', '铃星', '地空', '地劫'}
CS = '长生 沐浴 冠带 临官 帝旺 衰 病 死 墓 绝 胎 养'.split()
BS = '博士 力士 青龙 小耗 将军 奏书 飞廉 喜神 病符 大耗 伏兵 官府'.split()
SQ = '岁建 晦气 丧门 贯索 官符 小耗 大耗 龙德 白虎 天德 吊客 病符'.split()
JQ = '将星 攀鞍 岁驿 息神 华盖 劫煞 灾煞 天煞 指背 咸池 月煞 亡神'.split()

_BRIGHT = json.load(open(os.path.join(os.path.dirname(__file__), 'data', 'brightness_qs.json'), encoding='utf-8'))['table']


def _gz60(s: int, b: int) -> int:
    return next(i for i in range(60) if i % 10 == s and i % 12 == b)


def sanhe_group(b: int) -> int:
    """三合局分组的帝旺支：申子辰→子(0)，寅午戌→午(6)，巳酉丑→酉(9)，亥卯未→卯(3)。"""
    return {8: 0, 0: 0, 4: 0, 2: 6, 6: 6, 10: 6, 5: 9, 9: 9, 1: 9, 11: 3, 3: 3, 7: 3}[b]


def chart(month: int, day: int, hour: int, ys: int, yb: int, male: bool) -> dict:
    P = {b: [] for b in range(12)}

    def add(b, name):
        P[b % 12].append(name)

    ming = (2 + month - 1 - hour) % 12
    shen = (2 + month - 1 + hour) % 12
    yin = ((ys % 5) * 2 + 2) % 10
    stem = {b: (yin + (b - 2) % 12) % 10 for b in range(12)}
    ju = JU[NAYIN_WX[_gz60(stem[ming], ming) // 2]]
    x = 0
    while (day + x) % ju:
        x += 1
    q = (day + x) // ju
    zw = (2 + q - 1 + (-x if x % 2 else x)) % 12
    for off, n in [(0, '紫微'), (-1, '天机'), (-3, '太阳'), (-4, '武曲'), (-5, '天同'), (-8, '廉贞')]:
        add(zw + off, n)
    tf = (4 - zw) % 12
    for off, n in [(0, '天府'), (1, '太阴'), (2, '贪狼'), (3, '巨门'), (4, '天相'), (5, '天梁'), (6, '七杀'), (10, '破军')]:
        add(tf + off, n)
    # 六吉、禄马、六煞
    zuofu, youbi = (4 + month - 1) % 12, (10 - (month - 1)) % 12
    chang, qu = (10 - hour) % 12, (4 + hour) % 12
    add(zuofu, '左辅'); add(youbi, '右弼'); add(chang, '文昌'); add(qu, '文曲')
    kui, yue = {0: (1, 7), 4: (1, 7), 6: (1, 7), 1: (0, 8), 5: (0, 8), 2: (11, 9), 3: (11, 9), 7: (6, 2), 8: (3, 5), 9: (3, 5)}[ys]
    add(kui, '天魁'); add(yue, '天钺')
    lucun = {0: 2, 1: 3, 2: 5, 3: 6, 4: 5, 5: 6, 6: 8, 7: 9, 8: 11, 9: 0}[ys]
    add(lucun, '禄存'); add(lucun + 1, '擎羊'); add(lucun - 1, '陀罗')
    g = sanhe_group(yb)
    huo, ling = {6: (1, 3), 0: (2, 10), 9: (3, 10), 3: (9, 10)}[g]
    add(huo + hour, '火星'); add(ling + hour, '铃星')
    add(11 + hour, '地劫'); add(11 - hour, '地空')
    add({0: 2, 6: 8, 9: 11, 3: 5}[g], '天马')
    # 杂曜
    add(9 + month - 1, '天刑'); add(1 + month - 1, '天姚')
    hl = (3 - yb) % 12
    add(hl, '红鸾'); add(hl + 6, '天喜')
    add(4 + yb, '龙池'); add(10 - yb, '凤阁'); add(6 - yb, '天哭'); add(6 + yb, '天虚')
    gu = {11: (2, 10), 0: (2, 10), 1: (2, 10), 2: (5, 1), 3: (5, 1), 4: (5, 1), 5: (8, 4), 6: (8, 4), 7: (8, 4), 8: (11, 7), 9: (11, 7), 10: (11, 7)}[yb]
    add(gu[0], '孤辰'); add(gu[1], '寡宿')
    add(6 + hour, '台辅'); add(2 + hour, '封诰')
    add(zuofu + day - 1, '三台'); add(youbi - (day - 1), '八座')
    add(chang + day - 2, '恩光'); add(qu + day - 2, '天贵')
    add(ming + yb, '天才'); add(shen + yb, '天寿')
    add({1: 8, 2: 8, 3: 10, 4: 10, 5: 0, 6: 0, 7: 2, 8: 2, 9: 4, 10: 4, 11: 6, 12: 6}[month], '解神')
    add(10 - yb, '年解')
    add({1: 5, 5: 5, 9: 5, 2: 8, 6: 8, 10: 8, 3: 2, 7: 2, 11: 2, 4: 11, 8: 11, 12: 11}[month], '天巫')
    add([10, 5, 4, 2, 7, 3, 11, 7, 2, 6, 10, 2][month - 1], '天月')
    add([2, 0, 10, 8, 6, 4, 2, 0, 10, 8, 6, 4][month - 1], '阴煞')
    add([7, 4, 5, 2, 3, 9, 11, 9, 10, 6][ys], '天官'); add([9, 8, 0, 11, 3, 2, 6, 5, 6, 5][ys], '天福')
    add([5, 6, 0, 5, 6, 8, 2, 6, 9, 11][ys], '天厨')
    add(yb + 1, '天空')
    jie = {0: (8, 9), 5: (8, 9), 1: (6, 7), 6: (6, 7), 2: (4, 5), 7: (4, 5), 3: (2, 3), 8: (2, 3), 4: (0, 1), 9: (0, 1)}[ys]
    jie = jie if ys % 2 == 0 else (jie[1], jie[0])
    add(jie[0], '截空'); add(jie[1], '副截')
    head = (yb - ys) % 12
    xk = ((head + 10) % 12, (head + 11) % 12)
    xk = xk if yb % 2 == 0 else (xk[1], xk[0])
    add(xk[0], '旬空'); add(xk[1], '副旬')
    add({0: 5, 6: 5, 3: 5, 9: 5, 2: 9, 8: 9, 5: 9, 11: 9, 4: 1, 10: 1, 1: 1, 7: 1}[yb], '破碎')
    add([8, 9, 10, 5, 6, 7, 2, 3, 4, 11, 0, 1][yb], '蜚廉')
    add({0: 4, 6: 10, 9: 1, 3: 7}[g], '华盖')
    add({0: 9, 6: 3, 9: 6, 3: 0}[g], '咸池')
    add(9 + yb, '天德'); add(5 + yb, '月德')
    add(ming - 7, '天伤'); add(ming - 5, '天使')
    # 四化
    hua_list = SIHUA[ST[ys]].split()
    hua = dict(zip('禄权科忌', hua_list))
    star_hua = {s: k for k, s in hua.items()}
    forward = (ys % 2 == 0) == male
    names = {(ming - i) % 12: PALACES[i] for i in range(12)}
    cs_start = {2: 8, 3: 11, 4: 5, 5: 8, 6: 2}[ju]
    jiang = {0: 0, 6: 6, 9: 9, 3: 3}[g]
    side = {b: {} for b in range(12)}
    for i in range(12):
        d = 1 if forward else -1
        side[(cs_start + d * i) % 12]['长生'] = CS[i]
        side[(lucun + d * i) % 12]['博士'] = BS[i]
        side[(yb + i) % 12]['岁前'] = SQ[i]
        side[(jiang + i) % 12]['将前'] = JQ[i]
    xiao_start = {6: 4, 0: 10, 9: 7, 3: 1}[g]  # 寅午戌起辰，申子辰起戌，巳酉丑起未，亥卯未起丑
    palaces = []
    for i in range(12):
        b = (ming - i) % 12
        dx = (ju + 10 * i, ju + 10 * i + 9)
        db = (ming + (i if forward else -i)) % 12
        stars = []
        for n in P[b]:
            kind = 'major' if n in MAJOR else 'minor' if n in MINOR else 'adj'
            item = {'name': n, 'type': kind}
            if kind == 'major':
                item['brightness'] = _BRIGHT[n][b]
            if n in star_hua:
                item['hua'] = star_hua[n]
            if n in SHA:
                item['sha'] = True
            stars.append(item)
        palaces.append({'branch': BR[b], 'stem': ST[stem[b]], 'name': names[b],
                        'is_ming': b == ming, 'is_shen': b == shen, 'stars': stars, **side[b]})
    for p in palaces:
        b = BR.index(p['branch'])
        i = next(k for k in range(12) if (ming + (k if forward else -k)) % 12 == b)
        p['daxian'] = [ju + 10 * i, ju + 10 * i + 9]
        first = next(a for a in range(1, 13) if (xiao_start + (a - 1) * (1 if male else -1)) % 12 == b)
        p['xiaoxian_ages'] = [first + 12 * k for k in range(8)]
    # 宫干自化、对宫化入
    zihua, chongru = [], []
    for b in range(12):
        h = dict(zip('禄权科忌', SIHUA[ST[stem[b]]].split()))
        for k, s in h.items():
            if s in P[b]:
                zihua.append({'palace': names[b], 'star': s, 'hua': k})
            if s in P[(b + 6) % 12]:
                chongru.append({'from': names[b], 'to': names[(b + 6) % 12], 'star': s, 'hua': k})
    return {
        'ming_branch': BR[ming], 'shen_branch': BR[shen], 'shen_palace': names[shen],
        'ju': ju, 'ju_name': JU_NAME[ju], 'ziwei_branch': BR[zw], 'forward': forward,
        'yin_yang_gender': ('阳' if ys % 2 == 0 else '阴') + ('男' if male else '女'),
        'mingzhu': '贪狼 巨门 禄存 文曲 廉贞 武曲 破军 武曲 廉贞 文曲 禄存 巨门'.split()[ming],
        'shenzhu': '火星 天相 天梁 天同 文昌 天机 火星 天相 天梁 天同 文昌 天机'.split()[yb],
        'sihua': hua, 'palaces': palaces, 'zihua': zihua, 'chongru': chongru,
        'year_gz': ST[ys] + BR[yb], 'lunar_month_used': month, 'lunar_day': day, 'hour_branch': BR[hour],
    }


def palace_of(c: dict, star: str) -> str:
    for p in c['palaces']:
        if any(s['name'] == star for s in p['stars']):
            return p['name']
    return ''


def liunian(c: dict, year: int, birth_year: int, birth_month: int, birth_hour: int) -> dict:
    """某公历年（按其干支年）的流年命宫、流年四化落宫、所在大限、小限与流年斗君。"""
    ys, yb = (year - 4) % 10, (year - 4) % 12
    age = year - birth_year + 1
    by_branch = {p['branch']: p for p in c['palaces']}
    hua = dict(zip('禄权科忌', SIHUA[ST[ys]].split()))
    dx = next((p for p in c['palaces'] if p['daxian'][0] <= age <= p['daxian'][1]), None)
    xiao = next((p for p in c['palaces'] if age in p['xiaoxian_ages']), None)
    doujun = BR[(yb - (birth_month - 1) + birth_hour) % 12]
    return {
        'year': year, 'gz': ST[ys] + BR[yb], 'age_xu': age,
        'ming_palace': by_branch[BR[yb]]['name'], 'ming_branch': BR[yb],
        'sihua': [{'hua': k, 'star': s, 'palace': palace_of(c, s)} for k, s in hua.items()],
        'daxian_palace': dx['name'] if dx else '', 'daxian': dx['daxian'] if dx else None,
        'daxian_stem': dx['stem'] if dx else '',
        'xiaoxian_palace': xiao['name'] if xiao else '', 'doujun': doujun,
    }
