from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from database import init_db
import auth_router
import plan_router
import checkin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="30天减脂打卡 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 生产环境改为你的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router,    prefix="/auth",     tags=["认证"])
app.include_router(plan_router.router,    prefix="/plans",    tags=["计划"])
app.include_router(checkin_router.router, prefix="/checkins", tags=["打卡"])

@app.get("/")
def root():
    return {"message": "30天减脂打卡 API 运行中 🏃‍♀️"}
