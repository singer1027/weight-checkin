import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "checkin.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with get_conn() as conn:
        # 迁移1：email → phone
        cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if cols and "email" in cols and "phone" not in cols:
            print("[migration] email -> phone ...")
            conn.execute("ALTER TABLE users RENAME COLUMN email TO phone")
            conn.commit()
            print("[migration] done")

        # 迁移2：plans 表新增 start_weight / goal_weight
        plan_cols = [row[1] for row in conn.execute("PRAGMA table_info(plans)").fetchall()]
        if plan_cols and "start_weight" not in plan_cols:
            print("[migration] plans add start_weight / goal_weight ...")
            conn.execute("ALTER TABLE plans ADD COLUMN start_weight REAL")
            conn.execute("ALTER TABLE plans ADD COLUMN goal_weight  REAL")
            conn.commit()
            print("[migration] done")

        conn.executescript("""
        -- 用户表
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL,
            phone         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            goal_weight   REAL,
            avatar_url    TEXT,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- 打卡计划表（支持多轮）
        CREATE TABLE IF NOT EXISTS plans (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title         TEXT    NOT NULL DEFAULT '30天减脂计划',
            start_date    TEXT    NOT NULL,
            start_weight  REAL,           -- 计划开始时的体重（斤）
            goal_weight   REAL,           -- 本轮目标体重（斤）
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        -- 每日打卡记录表
        CREATE TABLE IF NOT EXISTS checkins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id     INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date        TEXT    NOT NULL,
            day_index   INTEGER NOT NULL,
            weight      REAL,
            waist       REAL,
            thigh       REAL,
            sports      TEXT,
            lunch       TEXT,
            snack       TEXT,
            dinner      TEXT,
            is_done     INTEGER NOT NULL DEFAULT 0,
            done_at     TEXT,
            calories    INTEGER,
            water_ml    INTEGER,
            sleep_hours REAL,
            mood        INTEGER,
            note        TEXT,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(plan_id, date)
        );
        """)
        conn.commit()
    print("[db] init done")
