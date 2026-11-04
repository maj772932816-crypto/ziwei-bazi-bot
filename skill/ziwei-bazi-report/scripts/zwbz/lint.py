"""解读防编造检查：把 narrative.json（或要发给用户的聊天回复）里提到的命理事实和 facts.json 逐项比对。

error：与排盘结果矛盾（必须改）；warn：可能有问题或写法不合规（建议改）。
只检查能可靠识别的说法，识别不了的句子不判断。
"""
import re

from .brief import daxian_rows
from .ziwei import MAJOR, MINOR, SIHUA

ST, BR = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'
STARS = MAJOR + MINOR
ADJ = ['红鸾', '天喜', '天刑', '天姚', '龙池', '凤阁', '天哭', '天虚', '孤辰', '寡宿', '台辅', '封诰', '三台', '八座',
       '恩光', '天贵', '天才', '天寿', '天巫', '天月', '阴煞', '天官', '天福', '天厨', '天空', '截空', '旬空', '破碎',
       '蜚廉', '华盖', '咸池', '天德', '月德', '天伤', '天使', '解神', '年解']
ALL_STARS = STARS + ADJ
PALACE_ALIAS = {'命宫': '命宫', '命': '命宫', '兄弟': '兄弟', '夫妻': '夫妻', '子女': '子女', '财帛': '财帛', '疾厄': '疾厄',
                '迁移': '迁移', '仆役': '仆役', '交友': '仆役', '奴仆': '仆役', '官禄': '官禄', '事业': '官禄', '田宅': '田宅',
                '福德': '福德', '父母': '父母'}
STAR_RE = '|'.join(sorted(ALL_STARS, key=len, reverse=True))
MAJOR_RE = '|'.join(MAJOR)
SIHUA_STAR_RE = '|'.join(sorted(STARS, key=len, reverse=True))
PALACE_RE = '|'.join(sorted((k for k in PALACE_ALIAS if k != '命'), key=len, reverse=True))
GZ_RE = f'[{ST}][{BR}]'
FORBIDDEN = ['死亡', '会死', '必死', '早死', '横死', '短命', '夭折', '绝症', '癌症', '血光之灾', '克死', '刑克父母', '妨夫', '克夫', '克妻', '命硬']
ABSOLUTE = ['注定', '必然', '一定会', '必定', '肯定会', '逃不掉', '躲不过']
# 年份段：八字大运按起运时间、紫微大限按虚岁，两边起止不同，不能合成一段
YR_RANGE = re.compile(r'((?:19|20|21)\d\d)\s*年?\s*(?:到|至|—|–|-|~|～)\s*((?:19|20|21)\d\d)')
SYS_KW = rf'(?:(?:{PALACE_RE})宫?大限|大限|[{ST}][{BR}]大?运(?!势|气)|大运)'
DY_KW = re.compile(rf'大运|[{ST}][{BR}]运(?!势|气)')
DX_KW = re.compile(r'大限')
BOTH_KW = re.compile(r'两边|两套|八字和紫微|紫微和八字|八字、紫微|紫微、八字|八字与紫微|紫微与八字')
ATT_BEFORE = re.compile(rf'({SYS_KW})\s*[（(：:]?\s*(?:约|大约|大概)?\s*$')
ATT_AFTER = re.compile(rf'^\s*年?\s*(?:的|是|为|走|行|属于|走的是|这步|这一步)?\s*(?:八字|紫微)?\s*(?:的)?\s*({SYS_KW})')
LABELS = {'偏旺', '偏弱', '身旺', '身弱', '中和', '中和略偏旺', '中和略偏弱', '从强', '从弱', '从旺', '从财', '从杀', '从儿', '化气'}


def _gz_of_year(y: int) -> str:
    i = (y - 4) % 60
    return ST[i % 10] + BR[i % 12]


def _texts(obj, path=''):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if not str(k).startswith('_'):
                yield from _texts(v, f'{path}.{k}' if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _texts(v, f'{path}[{i}]')


def _clauses(text: str):
    return [c for c in re.split(r'[。；;！？!?\n]', text) if c.strip()]


def _sentences(text: str):
    return [c for c in re.split(r'[。！？!?\n]', text) if c.strip()]


def _range_contexts(obj, path=''):
    """年份段按什么范围看：列表里的一张卡片、一行对照、一条回溯（标题、正文、依据、一致度合起来）；其余按句子。"""
    if isinstance(obj, dict) and re.search(r'\[\d+\]$', path):
        vals = [v for k, v in obj.items() if not str(k).startswith('_') and isinstance(v, str) and v.strip()]
        if vals:
            yield path, '：'.join(vals)
        return
    if isinstance(obj, str):
        for c in _sentences(obj):
            yield path, c
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if not str(k).startswith('_'):
                yield from _range_contexts(v, f'{path}.{k}' if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _range_contexts(v, f'{path}[{i}]')


class Facts:
    def __init__(self, f: dict):
        self.f = f
        self.bz = f['bazi']
        self.zw = f.get('ziwei')
        self.hua_birth, self.hua_any, self.star_branch, self.bright = set(), set(), {}, {}
        self.palace_branch, self.branch_palace = {}, {}
        if self.zw:
            for p in self.zw['palaces']:
                self.palace_branch[p['name']] = p['branch']
                self.branch_palace[p['branch']] = p['name']
                for s in p['stars']:
                    self.star_branch[s['name']] = p['branch']
                    if 'brightness' in s:
                        self.bright[s['name']] = s['brightness']
            self.hua_birth = {(s, k) for k, s in self.zw['sihua'].items()}
            self.hua_any |= self.hua_birth
            # 宫干、大限、流年、流月的四化：只收本盘实际出现的天干
            stems = {p['stem'] for p in self.zw['palaces']}
            stems |= {r['ziwei']['gz'][0] for r in f.get('years', []) if 'ziwei' in r}
            stems |= {m['gz'][0] for m in (f.get('months') or {}).get('ziwei', [])}
            for st in stems:
                self.hua_any |= {(s, k) for k, s in zip('禄权科忌', SIHUA[st].split())}
            self.daxian_hua = {f"{r['range'][0]}-{r['range'][1]}": {(x['star'], x['hua']) for x in r['sihua']} for r in daxian_rows(self.zw)}
            self.daxian = set(self.daxian_hua)
            self.zihua = {(z['star'], z['hua']) for z in self.zw['zihua'] + self.zw['chongru']}
            self.zihua_self = {(z['star'], z['hua']): z['palace'] for z in self.zw['zihua']}
        self.years = {str(r['year']): r for r in f.get('years', [])}
        self.year_hua = {k: {(x['star'], x['hua']) for x in r['ziwei']['sihua']} for k, r in self.years.items() if 'ziwei' in r}
        self.year_dx = {k: f"{r['ziwei']['daxian'][0]}-{r['ziwei']['daxian'][1]}" for k, r in self.years.items()
                        if 'ziwei' in r and r['ziwei'].get('daxian')}
        months = f.get('months') or {}
        self.month_hua = {str(months.get('year')): {(x['star'], x['hua']) for m in months.get('ziwei', []) for x in m['sihua']}} if months else {}
        self.dayun = {d['pillar'] for d in self.bz['dayun']}
        rows = [(d['pillar'], d['start_year']) for d in self.bz['dayun'] if d.get('start_year')]
        self.dayun_spans = [(p, y, rows[i + 1][1] if i + 1 < len(rows) else y + 10) for i, (p, y) in enumerate(rows)]
        by = (f.get('input') or {}).get('birth_year_for_age')
        self.daxian_spans = [(p['name'], by + p['daxian'][0] - 1, by + p['daxian'][1] - 1)
                             for p in sorted(self.zw['palaces'], key=lambda x: x['daxian'][0])] if self.zw and by else []
        if not self.zw:
            self.zihua_self = {}

    def spans_text(self, kind: str, y1: int, y2: int) -> str:
        if kind == 'dy':
            hit = [f'{p}运 {a}–{b}' for p, a, b in self.dayun_spans if a < y2 and b > y1]
            return '八字' + '、'.join(hit) if hit else ''
        hit = [f'{n}大限 {a}–{b}' for n, a, b in self.daxian_spans if a <= y2 and b >= y1]
        return '紫微' + '、'.join(hit) if hit else ''


def _check_clause(F, path: str, c: str, add):
    """逐句检查：四化、星曜落宫、亮度、命宫、身宫、局、大限岁数、年份干支、大运、四柱、写法。"""
    # 四化（写成「X化Y」或「X禄/X忌入某宫」都算）
    ctx_year = path.split('.')[1] if path.startswith('years.') else None
    if not ctx_year:
        ym = re.search(r'((?:19|20|21)\d\d)\s*年', c)
        ctx_year = ym.group(1) if ym and ym.group(1) in F.years else None
    ctx_dx = path.split('.')[2] if path.startswith('ziwei.daxian.') else None
    if not ctx_dx:
        dm_ = re.search(r'(\d{1,3})\s*[–\-—~到至]\s*(\d{1,3})\s*岁?\s*(?:的)?大限', c)
        ctx_dx = f'{dm_.group(1)}-{dm_.group(2)}' if dm_ else None
    for m in re.finditer(rf'({SIHUA_STAR_RE})(?:星)?(?:自)?(化)?(禄|权|科|忌)(?=化|入|进|落|在|与|和|并|叠|就|也|又|都|会|能|让|使|带|是|的|了|着|过|则|而|但|且|对|于|给|把|被|将|已|还|再|更|最|这|那|，|,|、|；|。|：|:|\s|$|）|\))', c):
        star, hua = m.group(1), m.group(3)
        if not F.zw or (not m.group(2) and star == '禄存'):
            continue
        before = c[:m.start()][-5:]
        if '自' in m.group(0):
            own = F.zihua_self.get((star, hua))
            if not own:
                add('error', path, c, f'本盘没有「{star}自化{hua}」；本盘的自化是 ' + ('、'.join(f"{v}{s_}自化{h}" for (s_, h), v in F.zihua_self.items()) or '没有'))
            elif '生年' in before:
                add('error', path, c, f'「{star}自化{hua}」来自{own}的宫干，不属于生年四化；写成「{own}{star}自化{hua}」')
            continue
        if (star, hua) not in F.hua_any:
            add('error', path, c, f'排盘结果里没有「{star}化{hua}」（生年、宫干、大限、流年都没有）')
        elif re.search(r'(生年|本命|出生|先天)', before) and (star, hua) not in F.hua_birth:
            add('error', path, c, f'生年四化里没有「{star}化{hua}」；生年四化是 ' + '、'.join(f'{s}化{k}' for s, k in sorted(F.hua_birth)))
        elif ctx_year and ctx_year in F.year_hua:
            allowed = F.year_hua[ctx_year] | F.hua_birth | F.zihua | F.daxian_hua.get(F.year_dx.get(ctx_year, ''), set()) | F.month_hua.get(ctx_year, set())
            if '流年' in before and (star, hua) not in F.year_hua[ctx_year]:
                add('error', path, c, f'{ctx_year} 年的流年四化是 ' + '、'.join(f'{s}化{k}' for s, k in sorted(F.year_hua[ctx_year])) + f'，没有「{star}化{hua}」')
            elif (star, hua) not in allowed:
                add('error', path, c, f'「{star}化{hua}」不属于 {ctx_year} 年的流年、当时大限或生年四化')
        elif ctx_dx and ctx_dx in F.daxian_hua:
            allowed = F.daxian_hua[ctx_dx] | F.hua_birth | F.zihua
            if (star, hua) not in allowed:
                add('error', path, c, f'「{star}化{hua}」不属于 {ctx_dx} 岁大限的四化或生年四化')
    # 星曜落宫：「X 在/落/入/坐/守/居 Y」
    if F.zw:
        for m in re.finditer(rf'({STAR_RE})(?:星)?(?:化?[禄权科忌])?(?:落|在|入|坐|守|居)(?:于|到)?(?:本命)?(?:的)?({PALACE_RE}|[{BR}])(?![{BR}])', c):
            star, pl = m.group(1), m.group(2)
            if '借' in c or star not in F.star_branch:
                continue
            sb = F.star_branch[star]
            want = F.palace_branch.get(PALACE_ALIAS.get(pl, ''), pl if pl in BR else None)
            if want and want != sb:
                add('error', path, c, f'「{star}」在{F.branch_palace[sb]}（{sb}宫），不在{pl}')
        # 「Y 宫有/坐/见 X」
        for m in re.finditer(rf'({PALACE_RE})(?:宫)?(?:[（(][{ST}][{BR}][）)])?(?:有|坐|见|主星为?|里的?|是)({STAR_RE})', c):
            pl, star = m.group(1), m.group(2)
            if '借' in c or star not in F.star_branch or PALACE_ALIAS.get(pl) not in F.palace_branch:
                continue
            if F.palace_branch[PALACE_ALIAS[pl]] != F.star_branch[star]:
                add('error', path, c, f'「{star}」不在{pl}宫，在{F.branch_palace[F.star_branch[star]]}')
        # 亮度
        for m in re.finditer(rf'({MAJOR_RE})(?:星)?(?:[（(](庙|旺|得|利|平|不|陷)[)）]|(入庙|落陷|庙旺))', c):
            star = m.group(1)
            actual = F.bright.get(star)
            claim = m.group(2) or m.group(3)
            ok = {'入庙': actual == '庙', '落陷': actual in ('陷', '不'), '庙旺': actual in ('庙', '旺')}.get(claim, actual == claim)
            if actual and not ok:
                add('error', path, c, f'「{star}」亮度是「{actual}」（《全书》表），不是「{claim}」')
        # 命宫干支、身宫、五行局
        for m in re.finditer(rf'命宫({GZ_RE})', c):
            real = F.zw['palaces'][0]['stem'] + F.zw['ming_branch']
            if m.group(1) != real:
                add('error', path, c, f'命宫是{real}，不是{m.group(1)}')
        for m in re.finditer(rf'身宫(?:在|落|落在|居)({PALACE_RE})', c):
            if PALACE_ALIAS.get(m.group(1)) != F.zw['shen_palace']:
                add('error', path, c, f"身宫在{F.zw['shen_palace']}，不在{m.group(1)}")
        for m in re.finditer(r'(水二|木三|金四|土五|火六)局', c):
            if m.group(0) != F.zw['ju_name']:
                add('error', path, c, f"本盘是{F.zw['ju_name']}，不是{m.group(0)}")
        for m in re.finditer(r'(\d{1,3})\s*[–\-—~到至]\s*(\d{1,3})\s*岁?\s*(?:的)?大限', c):
            if f'{m.group(1)}-{m.group(2)}' not in F.daxian:
                add('error', path, c, f'没有 {m.group(1)}–{m.group(2)} 岁这个大限')
    # 年份干支
    for m in re.finditer(rf'((?:19|20|21)\d\d)\s*年?\s*[（(]?\s*({GZ_RE})', c):
        y, g = int(m.group(1)), m.group(2)
        if _gz_of_year(y) != g:
            add('error', path, c, f'{y} 年是{_gz_of_year(y)}年，不是{g}')
    for m in re.finditer(rf'({GZ_RE})年?\s*[（(]\s*((?:19|20|21)\d\d)', c):
        g, y = m.group(1), int(m.group(2))
        if _gz_of_year(y) != g:
            add('error', path, c, f'{y} 年是{_gz_of_year(y)}年，不是{g}')
    # 八字
    for m in re.finditer(rf'({GZ_RE})大运', c):
        if m.group(1) not in F.dayun:
            add('error', path, c, f'本盘没有{m.group(1)}大运')
    for m in re.finditer(r'日主([甲乙丙丁戊己庚辛壬癸])', c):
        if m.group(1) != F.bz['day_master']:
            add('error', path, c, f"日主是{F.bz['day_master']}，不是{m.group(1)}")
    for m in re.finditer(rf'(年|月|日|时)柱({GZ_RE})', c):
        idx = '年月日时'.index(m.group(1))
        if idx < len(F.bz['pillars']) and F.bz['pillars'][idx] != m.group(2):
            add('error', path, c, f"{m.group(1)}柱是{F.bz['pillars'][idx]}，不是{m.group(2)}")
    # 写法
    for w in FORBIDDEN:
        if w in c and '不' + w not in c:
            add('error', path, c, f'不要写「{w}」这类恐吓或宿命的说法')
    for w in ABSOLUTE:
        if w in c and '不' + w not in c and '未必' not in c:
            add('warn', path, c, f'「{w}」太绝对，改成「倾向」「可能」「传统上认为」')


def _check_ranges(F, path: str, ctx: str, add):
    """年份段：写明属于八字大运还是紫微大限；两边起止不同，不能合成一段。"""
    found = [m for m in YR_RANGE.finditer(ctx) if int(m.group(2)) > int(m.group(1))]
    if not found or not F.dayun_spans:
        return
    has_dy, has_dx = bool(DY_KW.search(ctx)), bool(DX_KW.search(ctx))
    both = bool(BOTH_KW.search(ctx)) or (has_dy and has_dx)
    for m in found:
        y1, y2 = int(m.group(1)), int(m.group(2))
        rng = f'{y1}–{y2}'
        mb, ma = ATT_BEFORE.search(ctx[:m.start()]), ATT_AFTER.search(ctx[m.end():])
        kw = (mb or ma).group(1) if (mb or ma) else None
        att = ('dx' if '大限' in kw else 'dy') if kw else None
        dy = next((p for p, a, b in F.dayun_spans if y1 == a and y2 in (b - 1, b)), None)
        dx = next((n for n, a, b in F.daxian_spans if y1 == a and y2 in (b, b + 1)), None)
        kind = att or ('dx' if has_dx and not has_dy else 'dy' if has_dy and not has_dx else None)
        if kind == 'dx' and F.daxian_spans and not dx:
            if dy:
                add('error', path, ctx, f'{rng} 是八字{dy}运的年份，不是紫微大限；这段时间是{F.spans_text("dx", y1, y2)}')
            elif not any(a <= y1 and y2 <= b + 1 for _, a, b in F.daxian_spans):
                add('warn', path, ctx, f'{rng} 跨了不止一个紫微大限：{F.spans_text("dx", y1, y2)}')
        elif kind == 'dy' and not dy:
            if dx:
                add('error', path, ctx, f'{rng} 是紫微{dx}大限的年份，不是八字大运；这段时间是{F.spans_text("dy", y1, y2)}')
            elif not any(a <= y1 and y2 <= b for _, a, b in F.dayun_spans):
                add('warn', path, ctx, f'{rng} 跨了不止一步八字大运：{F.spans_text("dy", y1, y2)}')
        if att is None and F.daxian_spans and (dy is None) != (dx is None):
            if both and len(found) == 1:
                add('error', path, ctx, f'八字大运和紫微大限的起止年份不同，不能合成「{rng}」一段：{F.spans_text("dy", y1, y2)}；{F.spans_text("dx", y1, y2)}。'
                    '请分开写，例如「八字X运（起–止）、紫微X大限（起–止）」')
            elif kind is None and '十年' in ctx:
                which = f'八字{dy}运' if dy else f'紫微{dx}大限'
                add('warn', path, ctx, f'{rng} 是{which}的年份；这段时间{F.spans_text("dx" if dy else "dy", y1, y2)}。说的如果也包括另一边，请分开写')


def lint(facts: dict, nar: dict) -> list:
    F = Facts(facts)
    out = []

    def add(level, path, text, msg):
        snippet = text.strip()
        out.append({'level': level, 'where': path, 'text': snippet[:80] + ('…' if len(snippet) > 80 else ''), 'message': msg})

    # 结构
    for key in ('headline', 'summary', 'bazi', 'cross', 'checklist', 'advice') + (('ziwei',) if F.zw else ()):
        if not nar.get(key):
            add('warn', key, '', f'缺少 {key}，报告里这一部分会空着')
    n = len(nar.get('summary', []))
    if n and not 3 <= n <= 7:
        add('warn', 'summary', '', f'结论卡片 {n} 张，建议 4–6 张')
    n = len(nar.get('checklist', []))
    if n and not 6 <= n <= 15:
        add('warn', 'checklist', '', f'回溯核对 {n} 条，建议 10–13 条')
    for k in (nar.get('bazi', {}).get('dayun') or {}):
        if k not in F.dayun:
            add('error', f'bazi.dayun.{k}', k, f'没有「{k}」这步大运；本盘大运是 {"、".join(d["pillar"] for d in F.bz["dayun"][:8])}')
    if F.zw:
        for k in (nar.get('ziwei', {}).get('daxian') or {}):
            if k not in F.daxian:
                add('error', f'ziwei.daxian.{k}', k, f'没有「{k}」这个大限；本盘大限是 {"、".join(sorted(F.daxian, key=lambda x: int(x.split("-")[0])))}')
    for k in (nar.get('years') or {}):
        if k not in F.years:
            add('warn', f'years.{k}', k, f'逐年表里没有 {k} 年，这条提示不会显示')
    lab = (nar.get('bazi') or {}).get('strength_label')
    if lab and F.bz.get('strength') and lab != F.bz['strength']['label']:
        if lab not in LABELS:
            add('warn', 'bazi.strength_label', lab, '旺衰标签不是常用说法')
        else:
            add('warn', 'bazi.strength_label', lab, f"与程序参考标签「{F.bz['strength']['label']}」不同，确认 strength 正文写了理由")

    for path, text in _texts(nar):
        for c in _clauses(text):
            _check_clause(F, path, c, add)
    for path, ctx in _range_contexts(nar):
        _check_ranges(F, path, ctx, add)
    health = (nar.get('bazi') or {}).get('health', '')
    if health and not re.search(r'医生|就医|体检|检查', health):
        add('warn', 'bazi.health', health, '健康部分要提醒以医生为准、定期体检')
    return out


def lint_text(facts: dict, text: str, date=None) -> list:
    """检查要发给用户的聊天回复（追问的回答、报告前的结论段）。date：回答针对的那一天，用来认出当时的流年、流月四化。"""
    F = Facts(facts)
    if date and F.zw:
        import datetime
        from .flow import at
        d = date if isinstance(date, datetime.date) else datetime.date.fromisoformat(str(date))
        z = at(facts, d).get('ziwei')
        if z:
            yk = str(z['year']['year'])
            F.year_hua.setdefault(yk, {(x['star'], x['hua']) for x in z['year']['sihua']})
            F.month_hua[yk] = F.month_hua.get(yk, set()) | {(x['star'], x['hua']) for x in z['month']['sihua']}
            for st in (z['year']['gz'][0], z['month']['gz'][0]):
                F.hua_any |= {(s_, k) for k, s_ in zip('禄权科忌', SIHUA[st].split())}
    out = []

    def add(level, path, t, msg):
        snippet = t.strip()
        out.append({'level': level, 'where': path, 'text': snippet[:80] + ('…' if len(snippet) > 80 else ''), 'message': msg})
    for c in _clauses(text):
        _check_clause(F, '回复', c, add)
    for c in _sentences(text):
        _check_ranges(F, '回复', c, add)
    return out


def report(findings: list) -> str:
    if not findings:
        return '检查通过：没有发现与排盘结果矛盾的说法。'
    errs = [f for f in findings if f['level'] == 'error']
    warns = [f for f in findings if f['level'] == 'warn']
    lines = [f'发现 {len(errs)} 处错误、{len(warns)} 处提醒：']
    for f in errs + warns:
        lines.append(f"  [{'错误' if f['level'] == 'error' else '提醒'}] {f['where']}：{f['message']}" + (f"｜原文：{f['text']}" if f['text'] else ''))
    if errs:
        lines.append('错误必须改正后再生成报告。')
    return '\n'.join(lines)


MATCH_FORBIDDEN = ['不配', '不合适在一起', '注定分手', '会离婚', '必离', '相克到底', '八字不合', '打分', '几分', '配对指数']
REL_WORDS = '六合|相冲|相刑|相害|三合|半合|无合冲'


def lint_match(m: dict, nar: dict) -> list:
    """合盘解读检查：命宫关系、双方生年四化入对方哪一宫、禁用说法。"""
    out = []

    def add(level, path, text, msg):
        out.append({'level': level, 'where': path, 'text': text.strip()[:80], 'message': msg})
    zw = m.get('ziwei') or {}
    fly = {('甲方', x['star'], x['hua']): x['palace'] for x in zw.get('a_to_b', [])}
    fly.update({('乙方', x['star'], x['hua']): x['palace'] for x in zw.get('b_to_a', [])})
    rel = '；'.join(zw.get('ming_branches', {}).get('relation', []))
    pair = zw.get('ming_branches', {}).get('pair', '')
    for path, text in _texts(nar):
        for c in _clauses(text):
            for mm in re.finditer(rf'命宫(?:地支)?([{BR}])([{BR}])\s*({REL_WORDS})', c):
                a, b, word = mm.groups()
                if pair and {a, b} != set(pair):
                    add('error', path, c, f'双方命宫是 {pair[0]}、{pair[1]}，不是 {a}、{b}')
                elif rel and word not in rel and not (word == '无合冲' and '无' in rel):
                    add('error', path, c, f'双方命宫的关系是「{rel}」，不是「{word}」')
            for mm in re.finditer(rf'({SIHUA_STAR_RE})化(禄|权|科|忌)(?:落|入|进|在|飞入)(?:到)?(?:了)?(甲方|乙方)?(?:的)?({PALACE_RE})', c):
                star, hua, target, pl = mm.groups()
                subjects = re.findall(r'(?<![入落进在到])(甲方|乙方)', c[:mm.start()])
                who = subjects[-1] if subjects else ({'甲方': '乙方', '乙方': '甲方'}.get(target))
                if not who or who == target:
                    continue
                real = fly.get((who, star, hua))
                if real is None:
                    add('error', path, c, f'{who}的生年四化里没有「{star}化{hua}」')
                elif PALACE_ALIAS.get(pl) != real:
                    add('error', path, c, f'{who}的{star}化{hua}落在对方{real}宫，不是{pl}')
            for w in MATCH_FORBIDDEN + FORBIDDEN:
                if w in c and '不' + w not in c and '不要' + w not in c:
                    add('error', path, c, f'合盘不要写「{w}」这类定论或恐吓的话；只写合得来和要磨合的地方')
    return out
