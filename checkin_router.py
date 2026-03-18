from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
from datetime import datetime, date
from database import get_db
from auth_utils import current_user

router = APIRouter()


class CheckinUpsert(BaseModel):
    weight:      Optional[float] = None
    waist:       Optional[float] = None
    thigh:       Optional[float] = None
    sports:      Optional[List[str]] = None
    lunch:       Optional[str] = None
    snack:       Optional[str] = None
    dinner:      Optional[str] = None
    is_done:     Optional[bool] = None
    calories:    Optional[int]   = None
    water_ml:    Optional[int]   = None
    sleep_hours: Optional[float] = None
    mood:        Optional[int]   = None
    note:        Optional[str]   = None


def _row_to_dict(row: dict) -> dict:
    d = dict(row)
    if d.get("sports"):
        try:
            d["sports"] = json.loads(d["sports"])
        except Exception:
            d["sports"] = []
    # datetime/date 对象转字符串
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = str(v)
    return d


def _get_plan(plan_id: int, user_id: int, cur):
    cur.execute(
        "SELECT * FROM plans WHERE id=%s AND user_id=%s", (plan_id, user_id)
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "计划不存在或无权访问")
    return row


def _day_index(start_date: str, target_date: str) -> int:
    delta = date.fromisoformat(target_date) - date.fromisoformat(str(start_date))
    return delta.days + 1


@router.put("/{plan_id}/{checkin_date}", summary="新增或更新某天打卡")
def upsert_checkin(
    plan_id: int,
    checkin_date: str,
    body: CheckinUpsert,
    user: dict = Depends(current_user),
):
    with get_db() as cur:
        plan = _get_plan(plan_id, user["id"], cur)
        day_idx = _day_index(plan["start_date"], checkin_date)
        if not (1 <= day_idx <= 30):
            raise HTTPException(400, f"日期超出计划范围（第{day_idx}天）")

        cur.execute(
            "SELECT id FROM checkins WHERE plan_id=%s AND date=%s",
            (plan_id, checkin_date)
        )
        existing = cur.fetchone()

        sports_json = json.dumps(body.sports, ensure_ascii=False) if body.sports is not None else None
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        done_at = now if body.is_done else None

        if existing:
            updates = {}
            for field in ["weight", "waist", "thigh", "lunch", "snack", "dinner",
                          "calories", "water_ml", "sleep_hours", "mood", "note"]:
                val = getattr(body, field)
                if val is not None:
                    updates[field] = val
            if body.sports is not None:
                updates["sports"] = sports_json
            if body.is_done is not None:
                updates["is_done"] = int(body.is_done)
                updates["done_at"] = done_at
            updates["updated_at"] = now

            set_clause = ", ".join(f"{k}=%s" for k in updates)
            cur.execute(
                f"UPDATE checkins SET {set_clause} WHERE plan_id=%s AND date=%s",
                (*updates.values(), plan_id, checkin_date)
            )
        else:
            cur.execute("""
                INSERT INTO checkins
                  (plan_id, user_id, date, day_index,
                   weight, waist, thigh, sports,
                   lunch, snack, dinner,
                   is_done, done_at,
                   calories, water_ml, sleep_hours, mood, note,
                   updated_at)
                VALUES (%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s, %s,%s,%s,%s,%s, %s)
            """, (
                plan_id, user["id"], checkin_date, day_idx,
                body.weight, body.waist, body.thigh, sports_json,
                body.lunch, body.snack, body.dinner,
                int(body.is_done or 0), done_at,
                body.calories, body.water_ml, body.sleep_hours, body.mood, body.note,
                now
            ))

    return {"ok": True, "date": checkin_date, "day_index": day_idx}


@router.get("/{plan_id}/stats/summary", summary="统计摘要")
def stats(plan_id: int, user: dict = Depends(current_user)):
    with get_db() as cur:
        _get_plan(plan_id, user["id"], cur)
        cur.execute(
            "SELECT day_index, date, weight, is_done FROM checkins WHERE plan_id=%s ORDER BY day_index",
            (plan_id,)
        )
        rows = cur.fetchall()

    done_count = sum(1 for r in rows if r["is_done"])
    weights = [(str(r["date"]), r["weight"]) for r in rows if r["weight"]]
    weight_change = None
    if len(weights) >= 2:
        weight_change = round(weights[-1][1] - weights[0][1], 1)

    return {
        "done_count":    done_count,
        "total_days":    30,
        "weight_trend":  weights,
        "weight_change": weight_change,
    }


@router.get("/{plan_id}/{checkin_date}", summary="获取某天打卡详情")
def get_checkin(plan_id: int, checkin_date: str, user: dict = Depends(current_user)):
    with get_db() as cur:
        _get_plan(plan_id, user["id"], cur)
        cur.execute(
            "SELECT * FROM checkins WHERE plan_id=%s AND date=%s",
            (plan_id, checkin_date)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "该日期尚未打卡")
    return _row_to_dict(row)


@router.get("/{plan_id}", summary="获取计划的全部打卡记录")
def list_checkins(plan_id: int, user: dict = Depends(current_user)):
    with get_db() as cur:
        _get_plan(plan_id, user["id"], cur)
        cur.execute(
            "SELECT * FROM checkins WHERE plan_id=%s ORDER BY day_index",
            (plan_id,)
        )
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]
