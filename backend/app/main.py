"""FastAPI 入口：Data Entry Agent 后端"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .routers import settings, skills, recognize, tables

app = FastAPI(title="Data Entry Agent", version="0.2.0")

# 初始化 SQLite（建表 + 首次迁移旧文件数据）
database.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(skills.router)
app.include_router(recognize.router)
app.include_router(tables.router)


@app.get("/api/health")
def health():
    return {"ok": True}
