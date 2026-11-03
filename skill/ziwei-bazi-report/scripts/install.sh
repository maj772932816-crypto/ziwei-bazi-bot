#!/usr/bin/env bash
# 一键安装：Python 依赖（优先装进 scripts/.venv）、Node 依赖（交叉核对用），最后自检。可重复运行。
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
say() { printf '%s\n' "$*"; }

command -v python3 >/dev/null || { say '✗ 没有 python3，请先安装 Python 3.9 以上'; exit 2; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { say '✗ Python 版本低于 3.9'; exit 2; }

PY=python3
if [ -x .venv/bin/python ] || python3 -m venv .venv >/dev/null 2>&1; then
  PY="$DIR/.venv/bin/python"
  "$PY" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
  "$PY" -m pip install -q -r requirements.txt || { say '✗ pip 安装失败'; exit 2; }
else
  python3 -m pip install -q --user -r requirements.txt 2>/dev/null \
    || python3 -m pip install -q -r requirements.txt 2>/dev/null \
    || python3 -m pip install -q --break-system-packages -r requirements.txt \
    || { say '✗ pip 安装失败'; exit 2; }
fi
say "✓ Python 依赖已安装（$("$PY" -c 'import ephem, zstandard; print("ephem", ephem.__version__, "/ zstandard", zstandard.__version__)')）"

if command -v node >/dev/null && command -v npm >/dev/null; then
  node -e 'process.exit(parseInt(process.versions.node) >= 18 ? 0 : 1)' || { say '✗ Node.js 版本低于 18'; exit 2; }
  if [ -f package-lock.json ]; then npm ci --no-audit --no-fund --silent; else npm install --no-audit --no-fund --silent; fi \
    || { say '✗ npm 安装失败'; exit 2; }
  say '✓ Node 依赖已安装（iztro、lunar-javascript）'
else
  say '✗ 没有 Node.js 18+：交叉核对无法运行。请先安装 Node.js（如 apt install nodejs npm，或用 nvm），再重新运行本脚本'
  exit 2
fi

"$PY" zwbz.py selftest --n 30 && say '✓ 安装完成，可以使用：bash scripts/zwbz.sh run --help'
