"""开源「紫微斗数 13 维解读数据集 v4.0」查询（CC BY 4.0，需署名；正文里引用的倪海厦原话仅限非商用）。

数据：https://github.com/Renhuai123/ziwei-doushu/releases/tag/v4.0-13d
每个出生年份一个 year-YYYY.jsonl.zst（约 2 MB），首次用到时下载并按官方 SHA256SUMS.txt 校验，缓存在 ~/.cache/zwbz。
键：公历排盘日-时辰序号-性别，如 1990-05-20-7-female。数据集按时辰直接排盘，亮度用的是 2026-10-15 前的旧表。
"""
import hashlib
import json
import os
import re
import urllib.request

RELEASE = 'https://github.com/Renhuai123/ziwei-doushu/releases/download/v4.0-13d'
CACHE = os.environ.get('ZWBZ_CACHE', os.path.join(os.path.expanduser('~'), '.cache', 'zwbz'))
YEARS = range(1950, 2027)
DIMS = [('overview', '命格总览'), ('personality', '性格'), ('love', '感情'), ('career', '事业'), ('wealth', '财运'),
        ('health', '健康'), ('family', '兄弟'), ('children', '子女'), ('move', '迁移'), ('friends', '人际'),
        ('home', '田宅'), ('spirit', '福德'), ('parents', '父母')]
ATTRIBUTION = '本报告使用了 紫微斗数开源解读数据集 v4.0（674,976 张命盘 × 13 维），来源：https://github.com/Renhuai123/ziwei-doushu ，作者：王多鱼AI'


def _get(url: str, path: str):
    req = urllib.request.Request(url, headers={'User-Agent': 'zwbz/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r, open(path + '.part', 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(path + '.part', path)


def _sums() -> dict:
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, 'SHA256SUMS.txt')
    if not os.path.exists(p):
        _get(f'{RELEASE}/SHA256SUMS.txt', p)
    out = {}
    for line in open(p, encoding='utf-8'):
        parts = line.split()
        if len(parts) == 2:
            out[parts[1]] = parts[0]
    return out


def year_file(year: int) -> str:
    if year not in YEARS:
        raise ValueError(f'数据集只覆盖 1950–2026 年（排盘日为 {year}）')
    name = f'year-{year}.jsonl.zst'
    path = os.path.join(CACHE, name)
    want = _sums().get(name)
    def ok():
        if not os.path.exists(path):
            return False
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest() == want
    if not ok():
        _get(f'{RELEASE}/{name}', path)
        if not ok():
            raise RuntimeError(f'{name} 校验失败，与官方 SHA256SUMS 不一致')
    return path


def lookup(key: str):
    """按键查一条记录；查不到返回 None。需要 pip install zstandard。"""
    import zstandard
    path = year_file(int(key[:4]))
    needle = ('{"k":"' + key + '"').encode()
    dec = zstandard.ZstdDecompressor(max_window_size=2 ** 27)
    carry, parts = b'', None
    with open(path, 'rb') as f, dec.stream_reader(f) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            if parts is not None:
                end = chunk.find(b'\n')
                if end < 0:
                    parts.append(chunk)
                    continue
                parts.append(chunk[:end])
                return json.loads(b''.join(parts))
            data = carry + chunk
            i = data.find(needle)
            if i >= 0:
                end = data.find(b'\n', i)
                if end >= 0:
                    return json.loads(data[i:end])
                parts = [data[i:]]
                continue
            nl = data.rfind(b'\n')
            carry = data[nl + 1:] if nl >= 0 else data
    return json.loads(b''.join(parts)) if parts else None


def summarize(rec: dict) -> list:
    """每一维取「一句话定调」和白话总结的第一段。"""
    out = []
    for k, label in DIMS:
        text = rec['c'].get(k, '')
        tone = re.search(r'\*\*【一句话定调】\*\*\s*\n+(.+)', text)
        first = re.search(r'\*\*【[^】]*总览】\*\*\s*\n+(.+)', text)
        out.append({'key': k, 'label': label, 'tone': tone.group(1).strip() if tone else '',
                    'summary': first.group(1).strip() if first else ''})
    return out


def to_markdown(rec: dict) -> str:
    parts = [f"# 13 维解读原文（键 {rec['k']}）", '', f'> {ATTRIBUTION}。正文为数据集原文；数据集按时辰直接排盘、亮度用旧表，引用的倪海厦原话仅限非商用。', '']
    for k, label in DIMS:
        parts += ['---', '', f'## {label}', '', rec['c'].get(k, '').strip(), '']
    return '\n'.join(parts)
