import os
import uuid
import json
import time
import requests
import hashlib
import hmac
import base64
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import APIRouter, Depends, HTTPException, Request
from database import get_db
from auth_utils import current_user

router = APIRouter()

# ── 微信支付配置（从环境变量读取）──────────────────────────
APPID   = os.environ.get("WX_APPID", "")
MCHID   = os.environ.get("WX_MCHID", "")
API_V3_KEY = os.environ.get("WX_API_V3_KEY", "")
NOTIFY_URL = os.environ.get("WX_NOTIFY_URL", "https://weight-checkin.vercel.app/payment/notify")
AMOUNT_FEN = 99  # 0.99 元 = 99 分

# 私钥（apiclient_key.pem 内容，换行用 \n 存到环境变量）
_PRIVATE_KEY_PEM = os.environ.get("WX_PRIVATE_KEY", "")
_SERIAL_NO       = os.environ.get("WX_SERIAL_NO", "")


def _load_private_key():
    pem = _PRIVATE_KEY_PEM.replace("\\n", "\n").encode()
    return serialization.load_pem_private_key(pem, password=None)


def _sign(message: str) -> str:
    """用商户私钥对消息签名（RSA-SHA256）"""
    key = _load_private_key()
    sig = key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def _build_auth_header(method: str, url_path: str, body: str = "") -> str:
    nonce = uuid.uuid4().hex
    ts    = str(int(time.time()))
    msg   = f"{method}\n{url_path}\n{ts}\n{nonce}\n{body}\n"
    sig   = _sign(msg)
    return (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{MCHID}",'
        f'nonce_str="{nonce}",timestamp="{ts}",'
        f'serial_no="{_SERIAL_NO}",signature="{sig}"'
    )


def _wx_post(url_path: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False)
    auth = _build_auth_header("POST", url_path, body)
    resp = requests.post(
        f"https://api.mch.weixin.qq.com{url_path}",
        data=body.encode(),
        headers={
            "Authorization": auth,
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        timeout=10,
    )
    return resp.json()


def _wx_get(url_path: str) -> dict:
    auth = _build_auth_header("GET", url_path)
    resp = requests.get(
        f"https://api.mch.weixin.qq.com{url_path}",
        headers={"Authorization": auth, "Accept": "application/json"},
        timeout=10,
    )
    return resp.json()


# ── 创建订单 ────────────────────────────────────────────────
@router.post("/create", summary="创建支付订单")
def create_order(request: Request, user: dict = Depends(current_user)):
    if user.get("is_paid"):
        return {"already_paid": True}

    out_trade_no = f"WC{int(time.time()*1000)}{user['id']}"
    user_agent   = request.headers.get("user-agent", "")
    is_mobile    = any(k in user_agent.lower() for k in ["android", "iphone", "ipad", "mobile"])

    # 写入订单记录
    with get_db() as cur:
        cur.execute(
            "INSERT INTO orders(out_trade_no, user_id, amount) VALUES(%s,%s,%s)",
            (out_trade_no, user["id"], AMOUNT_FEN)
        )

    if is_mobile:
        # H5 支付（手机浏览器）
        result = _wx_post("/v3/pay/transactions/h5", {
            "appid":        APPID,
            "mchid":        MCHID,
            "description":  "30天减脂打卡 · 会员激活",
            "out_trade_no": out_trade_no,
            "notify_url":   NOTIFY_URL,
            "amount":       {"total": AMOUNT_FEN, "currency": "CNY"},
            "scene_info":   {"payer_client_ip": request.client.host, "h5_info": {"type": "Wap"}},
        })
        if "h5_url" not in result:
            raise HTTPException(502, f"微信支付H5创建失败: {result}")
        return {"type": "h5", "h5_url": result["h5_url"], "out_trade_no": out_trade_no}
    else:
        # Native 扫码支付（PC）
        result = _wx_post("/v3/pay/transactions/native", {
            "appid":        APPID,
            "mchid":        MCHID,
            "description":  "30天减脂打卡 · 会员激活",
            "out_trade_no": out_trade_no,
            "notify_url":   NOTIFY_URL,
            "amount":       {"total": AMOUNT_FEN, "currency": "CNY"},
        })
        if "code_url" not in result:
            raise HTTPException(502, f"微信支付Native创建失败: {result}")
        return {"type": "native", "code_url": result["code_url"], "out_trade_no": out_trade_no}


# ── 查询支付状态（前端轮询）────────────────────────────────
@router.get("/status/{out_trade_no}", summary="查询订单支付状态")
def query_status(out_trade_no: str, user: dict = Depends(current_user)):
    with get_db() as cur:
        cur.execute(
            "SELECT status FROM orders WHERE out_trade_no=%s AND user_id=%s",
            (out_trade_no, user["id"])
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "订单不存在")
    return {"status": row["status"], "is_paid": row["status"] == "paid"}


# ── 微信支付回调通知 ────────────────────────────────────────
@router.post("/notify", summary="微信支付回调", include_in_schema=False)
async def payment_notify(request: Request):
    body = await request.json()
    resource = body.get("resource", {})

    # 解密通知内容（AES-256-GCM）
    try:
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ciphertext    = base64.b64decode(resource["ciphertext"])
        nonce         = resource["nonce"].encode()
        associated    = resource["associated_data"].encode()
        key           = API_V3_KEY.encode()
        aesgcm        = AESGCM(key)
        plaintext     = aesgcm.decrypt(nonce, ciphertext, associated)
        data          = json.loads(plaintext)
    except Exception as e:
        return {"code": "FAIL", "message": str(e)}

    if data.get("trade_state") != "SUCCESS":
        return {"code": "SUCCESS", "message": "OK"}

    out_trade_no   = data["out_trade_no"]
    transaction_id = data["transaction_id"]
    now            = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as cur:
        cur.execute(
            "SELECT user_id FROM orders WHERE out_trade_no=%s", (out_trade_no,)
        )
        order = cur.fetchone()
        if not order:
            return {"code": "SUCCESS", "message": "OK"}

        cur.execute(
            "UPDATE orders SET status='paid', transaction_id=%s, paid_at=%s WHERE out_trade_no=%s",
            (transaction_id, now, out_trade_no)
        )
        cur.execute(
            "UPDATE users SET is_paid=1, paid_at=%s WHERE id=%s",
            (now, order["user_id"])
        )

    return {"code": "SUCCESS", "message": "OK"}
