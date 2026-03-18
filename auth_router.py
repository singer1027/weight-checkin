from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth_utils import hash_password, verify_password, create_token, current_user

router = APIRouter()


class RegisterBody(BaseModel):
    username: str
    phone: str
    password: str
    goal_weight: Optional[float] = None


class LoginBody(BaseModel):
    phone: str
    password: str


@router.post("/register", summary="注册")
def register(body: RegisterBody):
    if not body.phone.isdigit() or len(body.phone) != 11:
        raise HTTPException(400, "请输入正确的11位手机号")
    with get_db() as cur:
        cur.execute("SELECT id FROM users WHERE phone=%s", (body.phone,))
        if cur.fetchone():
            raise HTTPException(400, "该手机号已注册")
        cur.execute(
            "INSERT INTO users(username, phone, password_hash, goal_weight) VALUES(%s,%s,%s,%s)",
            (body.username, body.phone, hash_password(body.password), body.goal_weight)
        )
        user_id = cur.lastrowid
    token = create_token(user_id)
    return {"token": token, "user_id": user_id, "username": body.username}


@router.post("/login", summary="登录")
def login(body: LoginBody):
    with get_db() as cur:
        cur.execute("SELECT * FROM users WHERE phone=%s", (body.phone,))
        row = cur.fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "手机号或密码错误")
    token = create_token(row["id"])
    return {
        "token":       token,
        "user_id":     row["id"],
        "username":    row["username"],
        "goal_weight": row["goal_weight"],
    }


@router.get("/me", summary="获取当前用户信息")
def me(user: dict = Depends(current_user)):
    return {k: v for k, v in user.items() if k != "password_hash"}
