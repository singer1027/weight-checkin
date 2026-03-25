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
    DB_CONFIG["ssl"] = {"ca": "/etc/ssl/certs/ca-certificates.crt"}
    DB_CONFIG["ssl_verify_cert"] = True
    DB_CONFIG["ssl_verify_identity"] = False


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
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT          PRIMARY KEY AUTO_INCREMENT,
            username      VARCHAR(64)  NOT NULL,
            phone         VARCHAR(20)  NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            goal_weight   FLOAT,
            avatar_url    TEXT,
            is_paid       TINYINT      NOT NULL DEFAULT 0,
            paid_at       DATETIME,
            created_at    DATETIME     NOT NULL DEFAULT NOW()
        )
    """)

    cur.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_paid  TINYINT  NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS paid_at  DATETIME
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id            INT          PRIMARY KEY AUTO_INCREMENT,
            out_trade_no  VARCHAR(64)  NOT NULL UNIQUE,
            user_id       INT          NOT NULL,
            amount        INT          NOT NULL DEFAULT 99,
            status        VARCHAR(16)  NOT NULL DEFAULT 'pending',
            transaction_id VARCHAR(64),
            created_at    DATETIME     NOT NULL DEFAULT NOW(),
            paid_at       DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
