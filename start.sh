#!/usr/bin/env bash
# ============================================================
#  掌柜智库知识库 - 一键启动脚本 (Git Bash / Linux / macOS)
# ============================================================
set -e

# 切换到脚本所在目录（项目根）
cd "$(dirname "$0")"

echo
echo "============================================================"
echo "  掌柜智库知识库 正在启动..."
echo "============================================================"
echo

# 优先使用项目虚拟环境里的 python
if [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"      # Windows
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"              # Linux / macOS
else
    PY="python"
fi

if ! "$PY" --version >/dev/null 2>&1; then
    echo "[错误] 未找到可用的 Python 解释器。"
    exit 1
fi

echo "使用解释器: $PY"
echo "访问地址:   http://127.0.0.1:8000/"
echo "接口文档:   http://127.0.0.1:8000/docs"
echo
echo "按 Ctrl + C 可停止服务。"
echo "============================================================"
echo

exec "$PY" main.py
