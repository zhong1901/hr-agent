"""FastAPI 应用入口：初始化数据库、挂载路由与静态前端。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR
from .database import init_db, seed_question_bank
from .routers import auth, bank, interview, pay, records


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_path = BASE_DIR / "data" / "question_bank_seed.json"
    inserted = seed_question_bank(seed_path)
    if inserted:
        print(f"[题库] 已导入 {inserted} 条预设题目")
    yield


app = FastAPI(title="AI 面试备考助手", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(interview.router)
app.include_router(bank.router)
app.include_router(records.router)
app.include_router(pay.router)

static_dir = Path(BASE_DIR) / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    return FileResponse(str(static_dir / "index.html"))
