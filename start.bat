@echo off
REM ============================================================
REM  掌柜智库知识库 - 一键启动脚本 (Windows)
REM ============================================================
chcp 65001 >nul
setlocal

REM 切换到脚本所在目录（项目根）
cd /d "%~dp0"

echo.
echo ============================================================
echo   掌柜智库知识库 正在启动...
echo ============================================================
echo.

REM 优先使用项目虚拟环境里的 python，其次用系统 python
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

REM 校验 python 是否可用
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到可用的 Python 解释器。
    echo        请先安装 Python，或在项目内创建 .venv 虚拟环境。
    echo.
    pause
    exit /b 1
)

echo 使用解释器: %PY%
echo 访问地址:   http://127.0.0.1:8000/
echo 接口文档:   http://127.0.0.1:8000/docs
echo.
echo 按 Ctrl + C 可停止服务。
echo ============================================================
echo.

"%PY%" main.py

REM 若服务异常退出（非正常关闭），暂停以便查看错误
if errorlevel 1 (
    echo.
    echo [提示] 服务已退出，退出码 %errorlevel%。请检查上方错误信息。
    pause
)

endlocal
