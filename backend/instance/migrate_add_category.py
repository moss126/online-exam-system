# migrate_add_category.py
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "exam_system.db") # ← 改成绝对路径

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table});")
    return any(row[1] == column for row in cur.fetchall())

def table_exists(conn, table):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table,)
    )
    return cur.fetchone() is not None

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] DB not found: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        # 创建 categories 表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(120) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # 增加 questions.category_id
        if not column_exists(conn, "questions", "category_id"):
            cur.execute("ALTER TABLE questions ADD COLUMN category_id INTEGER;")
            print("[OK] questions.category_id added")
        else:
            print("[SKIP] questions.category_id already exists")
        conn.commit()
        print("[DONE] migration completed")
    except Exception as e:
        conn.rollback()
        print("[ERROR]", e)
    finally:
        conn.close()

if __name__ == "__main__":
    import os
    main()
