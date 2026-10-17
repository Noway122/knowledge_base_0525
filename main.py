import os
import sys

# 确保以项目根为导入根，直接 `python main.py` 也能找到 web/processor/utils 等包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

from web.api.app import app

if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8000"))
    print(f"掌柜智库知识库启动中... http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port)
