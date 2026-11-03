#!/usr/bin/env python3
"""生成发布包：dist/ziwei-bazi-report-<版本>.zip、dist/SHA256SUMS.txt，以及填好下载地址和校验值的 dist/SKILL.md。

用法：python3 tools/make_release.py --repo 用户名/仓库名 [--tag v1.1.0]

压缩包用固定的时间戳和文件顺序生成，同一份代码每次打出来的 SHA256 都一样。
dist/SKILL.md 是要粘贴给 Grok Bot 的技能文字；压缩包里的 SKILL.md 保留占位符（压缩包不能包含自己的校验值）。
"""
import argparse
import hashlib
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, 'skill', 'ziwei-bazi-report')
EXCLUDE = {'node_modules', '.venv', '__pycache__', 'work'}


def version() -> str:
    text = open(os.path.join(SKILL_DIR, 'scripts', 'zwbz', '__init__.py'), encoding='utf-8').read()
    return re.search(r"__version__ = '([^']+)'", text).group(1)


def build_zip(path: str):
    files = []
    for root, dirs, names in os.walk(SKILL_DIR):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE)
        for n in sorted(names):
            if n.endswith('.pyc'):
                continue
            full = os.path.join(root, n)
            files.append((full, os.path.join('ziwei-bazi-report', os.path.relpath(full, SKILL_DIR))))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for full, arc in files:
            info = zipfile.ZipInfo(arc, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if arc.endswith('.sh') else 0o644) << 16
            z.writestr(info, open(full, 'rb').read())
    return len(files)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repo', required=True, help='GitHub 仓库，如 someone/ziwei-bazi-bot')
    p.add_argument('--tag', help='Release 标签，默认 v<版本号>')
    a = p.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', a.repo):
        sys.exit('--repo 格式应为 用户名/仓库名')
    ver = version()
    tag = a.tag or f'v{ver}'
    dist = os.path.join(ROOT, 'dist')
    os.makedirs(dist, exist_ok=True)
    name = f'ziwei-bazi-report-{ver}.zip'
    zpath = os.path.join(dist, name)
    n = build_zip(zpath)
    sha = hashlib.sha256(open(zpath, 'rb').read()).hexdigest()
    url = f'https://github.com/{a.repo}/releases/download/{tag}/{name}'
    skill = open(os.path.join(SKILL_DIR, 'SKILL.md'), encoding='utf-8').read()
    for must in ('<RELEASE_URL>', '<SHA256>', f'技能版本 {ver}', f'zwbz {ver}'):
        if must not in skill:
            sys.exit(f'SKILL.md 里缺少「{must}」，请先把技能里的版本号改成 {ver}')
    open(os.path.join(dist, 'SKILL.md'), 'w', encoding='utf-8').write(skill.replace('<RELEASE_URL>', url).replace('<SHA256>', sha))
    open(os.path.join(dist, 'SHA256SUMS.txt'), 'w', encoding='utf-8').write(f'{sha}  {name}\n')
    print(f'版本 {ver}，{n} 个文件')
    print(f'压缩包：dist/{name}')
    print(f'SHA256：{sha}')
    print(f'下载地址：{url}')
    print('已生成 dist/SKILL.md（粘贴给 Grok Bot 的技能文字）和 dist/SHA256SUMS.txt')
    print(f'下一步：gh release create {tag} dist/{name} dist/SHA256SUMS.txt --repo {a.repo} --title "{tag}" --notes-file CHANGELOG.md')


if __name__ == '__main__':
    main()
