import os
import pymysql
import pymysql.cursors
from contextlib import contextmanager

DB_CONFIG = {
    "host":        os.environ.get("DB_HOST", "localhost"),
    "port":        int(os.environ.get("DB_PORT", "3306")),
    "user":        os.environ.get("DB_USER", "root"),
    "password":    os.environ.get("DB_PASSWORD", ""),
    "database":    os.environ.get("DB_NAME", "checkin"),
    "charset":     "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit":  False,
}

if os.environ.get("DB_SSL", "false").lower() == "true":
    DB_CONFIG["ssl"] = {"check_hostname": False}


@contextmanager
def get_db():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    # 先不指定 database，用于确保库存在
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    cur = conn.cursor()
    db_name = DB_CONFIG["database"]
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{db_name}`")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT          PRIMARY KEY AUTO_INCREMENT,
            username      VARCHAR(64)  NOT NULL,
            phone         VARCHAR(20)  NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            goal_weight   FLOAT,
            avatar_url    TEXT,
            created_at    DATETIME     NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id           INT          PRIMARY KEY AUTO_INCREMENT,
            user_id      INT          NOT NULL,
            title        VARCHAR(128) NOT NULL DEFAULT '30天减脂计划',
            start_date   DATE         NOT NULL,
            start_weight FLOAT,
            goal_weight  FLOAT,
            is_active    TINYINT      NOT NULL DEFAULT 1,
            created_at   DATETIME     NOT NULL DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id          INT      PRIMARY KEY AUTO_INCREMENT,
            plan_id     INT      NOT NULL,
            user_id     INT      NOT NULL,
            date        DATE     NOT NULL,
            day_index   INT      NOT NULL,
            weight      FLOAT,
            waist       FLOAT,
            thigh       FLOAT,
            sports      TEXT,
            lunch       TEXT,
            snack       TEXT,
            dinner      TEXT,
            is_done     TINYINT  NOT NULL DEFAULT 0,
            done_at     DATETIME,
            calories    INT,
            water_ml    INT,
            sleep_hours FLOAT,
            mood        INT,
            note        TEXT,
            updated_at  DATETIME NOT NULL DEFAULT NOW(),
            UNIQUE KEY uq_plan_date (plan_id, date),
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[db] init done")
