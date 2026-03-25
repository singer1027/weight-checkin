import os
import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth_utils import current_user

router = APIRouter()

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change_me_admin_secret")


def _gen_code() -> str:
    """生成6位大写字母+数字验证码"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ── 获取付款信息（用户登录后调用）────────────────────────
@router.get("/info", summary="获取付款验证码和二维码")
def payment_info(user: dict = Depends(current_user)):
    if user.get("is_paid"):
        return {"is_paid": True}

    # 如果还没有验证码，生成一个
    with get_db() as cur:
        cur.execute("SELECT verify_code FROM users WHERE id=%s", (user["id"],))
        row = cur.fetchone()
        code = row["verify_code"] if row and row["verify_code"] else None

        if not code:
            code = _gen_code()
            cur.execute("UPDATE users SET verify_code=%s WHERE id=%s", (code, user["id"]))

    return {
        "is_paid":     False,
        "verify_code": code,
        "amount":      "0.99",
        "tip":         f"请扫码支付 ¥0.99，转账备注填写：{code}",
    }


# ── 管理员激活用户（你专用）─────────────────────────────
@router.post("/activate", summary="管理员激活用户")
def activate_user(
    code:   str = Query(..., description="用户验证码"),
    secret: str = Query(..., description="管理员密钥"),
):
    if secret != ADMIN_SECRET:
        raise HTTPException(403, "无权操作")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as cur:
        cur.execute("SELECT id, username, is_paid FROM users WHERE verify_code=%s", (code,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, f"验证码 {code} 不存在")
        if user["is_paid"]:
            return {"ok": True, "message": f"{user['username']} 已是付费用户"}
        cur.execute(
            "UPDATE users SET is_paid=1, paid_at=%s WHERE id=%s",
            (now, user["id"])
        )

    return {"ok": True, "message": f"已激活用户：{user['username']}（验证码：{code}）"}


# ── 查询自己是否已付费（前端轮询）───────────────────────
@router.get("/status", summary="查询付费状态")
def payment_status(user: dict = Depends(current_user)):
    return {"is_paid": bool(user.get("is_paid"))}
