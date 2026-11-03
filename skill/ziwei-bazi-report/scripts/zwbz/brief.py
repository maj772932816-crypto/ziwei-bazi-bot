"""把 facts.json 压成一段给模型读的中文要点（写分析时以此为准，不要另起炉灶排盘）。"""
from .ziwei import SIHUA, palace_of


def daxian_rows(zw: dict) -> list:
    rows = []
    for p in sorted(zw['palaces'], key=lambda x: x['daxian'][0]):
        hua = dict(zip('禄权科忌', SIHUA[p['stem']].split()))
        rows.append({'range': p['daxian'], 'palace': p['name'], 'gz': p['stem'] + p['branch'],
                     'sihua': [{'hua': k, 'star': s, 'palace': palace_of(zw, s)} for k, s in hua.items()]})
    return rows


def _stars(p, kind):
    out = []
    for s in p['stars']:
        if s['type'] != kind:
            continue
        t = s['name']
        if 'brightness' in s:
            t += f"({s['brightness']})"
        if 'hua' in s:
            t += f"化{s['hua']}"
        out.append(t)
    return '、'.join(out)


def brief(f: dict) -> str:
    i, bz, zw = f['input'], f['bazi'], f.get('ziwei')
    L = []
    g = '男' if i['gender'] == 'male' else '女'
    place = i['place']
    L.append('【基本】')
    L.append(f"{i.get('name') or '命主'}，{g}；公历 {i['solar_date']} {i['time_input'] or ''}；出生地 {(place['province'] + place['city']) if place else '未提供'}")
    if i['true_solar']:
        L.append(f"排盘基准：真太阳时 {i['basis_time']}（经度修正 {i['true_solar']['longitude_minutes']:+} 分，均时差 {i['true_solar']['eot_minutes']:+} 分）")
    else:
        L.append(f"排盘基准：{i['basis']} {i['basis_time'] or ''}")
    L.append(f"农历：{f['lunar']['text']}；八字：{' '.join(bz['pillars'])}")
    if zw:
        L.append(f"紫微：{zw['yin_yang_gender']}，{zw['ju_name']}，命宫{zw['palaces'][0]['stem']}{zw['ming_branch']}，身宫在{zw['shen_palace']}，命主{zw['mingzhu']}，身主{zw['shenzhu']}")
    st = f.get('status') or {}
    if st:
        label = {'ok': '可以继续', 'confirm': '先问用户', 'stop': '停下'}[st['status']]
        L.append(f"【状态】{label}：{st['next']}")
        for q in st.get('questions', []):
            L.append(f'  要问用户：{q}')
    L.append('【核对】' + '；'.join(f"{c['item']}：{'通过' if c['status'] == 'ok' else '注意' if c['status'] == 'warn' else '不一致'}（{c['result']}）" for c in f['checks']))
    if f.get('warnings'):
        L.append('【需要确认】' + '；'.join(f['warnings']))
    if f.get('notes'):
        L.append('【口径说明】' + '；'.join(f['notes']))
    L.append('【八字】日主 ' + bz['day_master'])
    for d in bz['detail']:
        hid = ' '.join(h['stem'] + h['god'] for h in d['hidden'])
        L.append(f"  {d['pos']}柱 {d['pillar']}：干为{d['stem_god']}；藏干 {hid}；日主在此{d['stage']}；纳音{d['nayin']}")
    L.append(f"  空亡：日柱旬空{bz['kongwang']['日柱旬空']}，年柱旬空{bz['kongwang']['年柱旬空']}")
    L.append('  神煞：' + '，'.join(f'{k}{v}' for k, v in bz['shensha'].items() if v))
    L.append('  原局作用：' + ('；'.join(bz['relations']) or '无明显合冲刑害'))
    s = bz.get('strength')
    if s:
        L.append(f"  五行计分 {s['score']}；生扶 {s['self_vs_other'][0]} 对 克泄耗 {s['self_vs_other'][1]}（月令加权后 {s['self_vs_other_month_weighted'][0]} 对 {s['self_vs_other_month_weighted'][1]}）；"
                 f"{'得令' if s['de_ling'] else '不得令'}；参考标签：{s['label']}；{s['tiaohou']}")
    y = bz['yun']
    L.append(f"  大运{'顺' if y['forward'] else '逆'}排，起运约 {y['start_age']} 岁（{y['start_date']}）：")
    for d in bz['dayun'][:8]:
        L.append(f"    {d['pillar']}（{d['start'][:7]} 起，约 {d.get('start_age', d['start_age_xu'])} 岁，{d['stem_god']}/{d['branch_god']}）："
                 + ('；'.join(d.get('relations', [])) or '与原局无明显作用'))
    if zw:
        L.append('【紫微十二宫】（从命宫起逆排）')
        for p in zw['palaces']:
            tag = ('[命]' if p['is_ming'] else '') + ('[身]' if p['is_shen'] else '')
            mj = _stars(p, 'major') or '空宫'
            L.append(f"  {p['name']}{tag} {p['stem']}{p['branch']}：主星 {mj}；吉煞 {_stars(p, 'minor') or '无'}；杂曜 {_stars(p, 'adj')}；"
                     f"大限 {p['daxian'][0]}–{p['daxian'][1]}；{p['长生']}")
        L.append('  生年四化：' + '，'.join(f"{s}化{k}在{palace_of(zw, s)}" for k, s in zw['sihua'].items()))
        L.append('  宫干自化：' + ('，'.join(f"{z['palace']}{z['star']}自化{z['hua']}" for z in zw['zihua']) or '无'))
        L.append('  对宫化入：' + ('，'.join(f"{z['from']}化{z['hua']}入{z['to']}（{z['star']}）" for z in zw['chongru']) or '无'))
        L.append('【大限】')
        for r in daxian_rows(zw):
            L.append(f"  {r['range'][0]}–{r['range'][1]} 岁 {r['palace']}（{r['gz']}）：" + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in r['sihua']))
    if f.get('years'):
        L.append('【逐年】')
        for r in f['years']:
            line = f"  {r['year']} {r['gz']} 虚岁{r['age_xu']} 大运{r['dayun']}：{r['gods']}；" + ('；'.join(r['bazi_relations']) or '与原局无明显作用')
            if 'ziwei' in r:
                z = r['ziwei']
                line += f" ｜紫微 流年命宫在{z['ming_palace']}，大限{z['daxian_palace']}，小限{z['xiaoxian_palace']}，" + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in z['sihua'])
            L.append(line)
    mo = f.get('months')
    if mo:
        L.append(f"【流月 {mo['year']}】八字按节气月：")
        for r in mo['bazi']:
            L.append(f"  {r['jie']}起 {r['start'][5:10]}–{r['end'][5:10]} {r['pillar']}（{r['gods']}）：" + ('；'.join(r['relations']) or '与原局无明显作用'))
        if mo.get('ziwei'):
            L.append('  紫微按农历月（流年斗君起正月）：')
            for r in mo['ziwei']:
                L.append(f"  {r['label']} {r['start'][5:]}–{r['end'][5:]} {r['gz']}：流月命宫在{r['palace']}；" + '，'.join(f"{x['star']}化{x['hua']}入{x['palace']}" for x in r['sihua']))
    ds = f.get('dataset')
    if ds and ds.get('dims'):
        L.append('【开源数据集 13 维一句话】（仅作第三方参考，亮度用旧表，与事实冲突时以事实为准）')
        for d in ds['dims']:
            L.append(f"  {d['label']}：{d['tone']}")
    return '\n'.join(L)
