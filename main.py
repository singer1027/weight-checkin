from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from database import init_db
import auth_router
import plan_router
import checkin_router
import os

init_db()

app = FastAPI(
    title="30天减脂打卡 API",
    version="1.0.0",
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

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "30day-checkin-new.html"))
