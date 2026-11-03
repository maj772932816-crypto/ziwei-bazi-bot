#!/usr/bin/env bash
# 包装脚本：优先用 install.sh 建好的虚拟环境运行 zwbz.py
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$DIR/.venv/bin/python" ]; then exec "$DIR/.venv/bin/python" "$DIR/zwbz.py" "$@"; fi
exec python3 "$DIR/zwbz.py" "$@"
