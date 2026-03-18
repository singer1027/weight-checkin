"""
一次性数据导入脚本
把 CSV 历史数据导入到 singer 用户的「3-6减肥计划」中

使用方法：
  把此文件放到 backend 文件夹，然后运行：
  py import_data.py
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "checkin.db"

# ── 历史打卡数据（从 CSV 整理而来）──────────────────────
CSV_DATA = [
    {"date": "2026-03-06", "weight": 105.7, "waist": None,  "thigh": None,  "sports": ["公园探险快走"],              "is_done": True,  "lunch": "米饭+1个去皮鸡腿+半个蛋+水煮圆白菜",     "snack": "-",          "dinner": "关东煮（萝卜+魔芋2+笋）+鸡腿串+小花卷"},
    {"date": "2026-03-07", "weight": 105.3, "waist": 74.0,  "thigh": 54.0,  "sports": [],                           "is_done": True,  "lunch": "米饭+鸡胸肉+土豆丝",                    "snack": "6个瓜子",     "dinner": "麦片无糖酸奶+半截四川猪肉肠"},
    {"date": "2026-03-08", "weight": 104.5, "waist": 73.5,  "thigh": 53.5,  "sports": ["游泳"],                     "is_done": True,  "lunch": "杂粮包+炒杂菜+鱼香肉丝",                "snack": "虾片+好有趣饼干", "dinner": "鸡胸肉+1/8大饼+2个鸭翅+卤菜"},
    {"date": "2026-03-09", "weight": 105.1, "waist": 74.5,  "thigh": 52.0,  "sports": ["羽毛球社交局"],             "is_done": True,  "lunch": "米饭+锅包肉+5只虾+青菜芹菜",            "snack": "半个香蕉",    "dinner": "鸡胸肉+无糖酸奶"},
    {"date": "2026-03-10", "weight": 104.7, "waist": 74.5,  "thigh": 52.0,  "sports": ["羽毛球社交局"],             "is_done": True,  "lunch": "杂粮饭+鸡胸肉+南瓜",                    "snack": "半个苹果",    "dinner": "南瓜糊+水果一把+牛肉串5个+青梅酒"},
    {"date": "2026-03-11", "weight": 105.4, "waist": None,  "thigh": None,  "sports": ["健身操蹦迪夜"],             "is_done": True,  "lunch": "米饭+水煮白菜+瘦猪肉+红豆粥",           "snack": "",           "dinner": "四分之一三明治"},
    {"date": "2026-03-12", "weight": 103.8, "waist": 75.5,  "thigh": 50.5,  "sports": ["健身操蹦迪夜","羽毛球社交局"], "is_done": True, "lunch": "米饭+小白菜+圆白菜+肉类",              "snack": "",           "dinner": "去皮鸡腿+酸奶"},
    {"date": "2026-03-13", "weight": 103.8, "waist": 75.5,  "thigh": 50.5,  "sports": ["健身操蹦迪夜"],             "is_done": True,  "lunch": "米饭+2蔬菜+蘑菇+豆角+牛肉+排骨",        "snack": "无糖酸奶",    "dinner": "鸡胸肉+生菜+黄瓜"},
    {"date": "2026-03-14", "weight": 104.2, "waist": 74.5,  "thigh": 50.5,  "sports": [],                           "is_done": True,  "lunch": "米饭蒿子杆，排骨，豆角",                 "snack": "",           "dinner": "生菜鸡胸肉面条"},
    {"date": "2026-03-15", "weight": 104.0, "waist": 74.5,  "thigh": 50.0,  "sports": [],                           "is_done": True,  "lunch": "火锅，白菜，牛肉，虾滑，毛肚，海带，金针菇", "snack": "",         "dinner": "小花卷，小橘子"},
    {"date": "2026-03-16", "weight": 103.5, "waist": 74.5,  "thigh": 50.0,  "sports": [],                           "is_done": False, "lunch": "",                                       "snack": "",           "dinner": ""},
]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def main():
    conn = get_conn()

    # 1. 找到 singer 用户
    user = conn.execute("SELECT * FROM users WHERE username=?", ("singer",)).fetchone()
    if not user:
        print("❌ 找不到用户名为 singer 的用户，请先在网页上注册账号后再运行此脚本。")
        conn.close()
        return
    user_id = user["id"]
    print(f"✅ 找到用户：{user['username']} (id={user_id})")

    # 2. 找到开始日期为 2026-03-06 的计划
    plan = conn.execute(
        "SELECT * FROM plans WHERE user_id=? AND start_date=? ORDER BY id DESC LIMIT 1",
        (user_id, "2026-03-06")
    ).fetchone()
    if not plan:
        print("❌ 找不到开始日期为 2026-03-06 的计划。")
        print("   请先在网页上用 singer 账号创建一个开始日期为 2026-03-06 的计划，再运行此脚本。")
        conn.close()
        return
    plan_id = plan["id"]
    print(f"✅ 找到计划：{plan['title']} (id={plan_id}, 开始={plan['start_date']})")

    # 3. 逐条写入打卡数据
    from datetime import date
    inserted = 0
    updated  = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in CSV_DATA:
        d         = row["date"]
        day_index = (date.fromisoformat(d) - date.fromisoformat("2026-03-06")).days + 1
        sports_json = json.dumps(row["sports"], ensure_ascii=False)
        done_at     = now if row["is_done"] else None

        existing = conn.execute(
            "SELECT id FROM checkins WHERE plan_id=? AND date=?", (plan_id, d)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE checkins SET
                  weight=?, waist=?, thigh=?, sports=?,
                  lunch=?, snack=?, dinner=?,
                  is_done=?, done_at=?, updated_at=?
                WHERE plan_id=? AND date=?
            """, (
                row["weight"], row["waist"], row["thigh"], sports_json,
                row["lunch"], row["snack"], row["dinner"],
                int(row["is_done"]), done_at, now,
                plan_id, d
            ))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO checkins
                  (plan_id, user_id, date, day_index,
                   weight, waist, thigh, sports,
                   lunch, snack, dinner,
                   is_done, done_at, updated_at)
                VALUES (?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?)
            """, (
                plan_id, user_id, d, day_index,
                row["weight"], row["waist"], row["thigh"], sports_json,
                row["lunch"], row["snack"], row["dinner"],
                int(row["is_done"]), done_at, now
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"\n🎉 导入完成！新增 {inserted} 条，更新 {updated} 条")
    print("   刷新网页即可看到历史数据 ✨")

if __name__ == "__main__":
    main()
