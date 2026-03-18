from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth_utils import current_user

router = APIRouter()


class PlanCreate(BaseModel):
    title: str = "30天减脂计划"
    start_date: str                       # YYYY-MM-DD
    start_weight: Optional[float] = None  # 当前体重（斤）
    goal_weight:  Optional[float] = None  # 目标体重（斤）


@router.post("", summary="创建新一轮计划")
def create_plan(body: PlanCreate, user: dict = Depends(current_user)):
    with get_db() as cur:
        cur.execute("UPDATE plans SET is_active=0 WHERE user_id=%s", (user["id"],))
        cur.execute(
            "INSERT INTO plans(user_id, title, start_date, start_weight, goal_weight) VALUES(%s,%s,%s,%s,%s)",
            (user["id"], body.title, body.start_date, body.start_weight, body.goal_weight)
        )
        plan_id = cur.lastrowid
    return {
        "plan_id":      plan_id,
        "title":        body.title,
        "start_date":   body.start_date,
        "start_weight": body.start_weight,
        "goal_weight":  body.goal_weight,
    }


@router.get("", summary="获取我的所有计划")
def list_plans(user: dict = Depends(current_user)):
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM plans WHERE user_id=%s ORDER BY created_at DESC",
            (user["id"],)
        )
        rows = cur.fetchall()
    return rows


@router.get("/active", summary="获取当前活跃计划")
def active_plan(user: dict = Depends(current_user)):
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM plans WHERE user_id=%s AND is_active=1 ORDER BY created_at DESC LIMIT 1",
            (user["id"],)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "暂无活跃计划，请先创建")
    return row


@router.delete("/{plan_id}", summary="删除计划（及其所有打卡）")
def delete_plan(plan_id: int, user: dict = Depends(current_user)):
    with get_db() as cur:
        cur.execute(
            "SELECT id FROM plans WHERE id=%s AND user_id=%s", (plan_id, user["id"])
        )
        if not cur.fetchone():
            raise HTTPException(404, "计划不存在")
        cur.execute("DELETE FROM plans WHERE id=%s", (plan_id,))
    return {"ok": True}
