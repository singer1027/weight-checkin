import hashlib
import hmac
import json
import base64
import time
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import get_conn

SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR"  # 生产环境务必改成随机长字符串
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7天


# ── 密码哈希 ────────────────────────────────────────────
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ── 简易 JWT（无依赖版，生产可换 python-jose）───────────
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _sign(msg: str) -> str:
    return _b64(hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).digest())

def create_token(user_id: int) -> str:
    header  = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS}).encode())
    sig = _sign(f"{header}.{payload}")
    return f"{header}.{payload}.{sig}"

def decode_token(token: str) -> dict:
    try:
        header, payload, sig = token.split(".")
        if _sign(f"{header}.{payload}") != sig:
            raise ValueError("签名不匹配")
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        if data["exp"] < time.time():
            raise ValueError("Token 已过期")
        return data
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"无效凭证：{e}")


# ── 依赖注入：获取当前登录用户 ──────────────────────────
bearer = HTTPBearer()

def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    data = decode_token(cred.credentials)
    user_id = data["sub"]
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    return dict(row)
