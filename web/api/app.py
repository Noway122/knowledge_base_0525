from pathlib import Path

from fastapi import FastAPI
from starlette.responses import FileResponse, RedirectResponse
from starlette.middleware.cors import CORSMiddleware

from web.api.routers import import_router, query_router

app = FastAPI(
    title="掌柜智库知识库",
    description="上传文件入库 + 知识库检索问答 统一服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router.router)
app.include_router(query_router.router)


@app.get("/", include_in_schema=False)
async def index():
    html_path = Path(__file__).absolute().parent.parent / "page" / "index.html"
    if not html_path.exists():
        return RedirectResponse(url="/docs")
    return FileResponse(html_path)
