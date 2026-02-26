# backend/fix_exam_status.py
from sqlalchemy import text
from app import app
from models import db, Exam

# 把枚举列中不是 ACTIVE/INACTIVE 的值统一修成 INACTIVE
with app.app_context():
    table = Exam.__tablename__
    sql = text(f"UPDATE {table} SET status='INACTIVE' WHERE status NOT IN ('ACTIVE','INACTIVE')")
    db.session.execute(sql)
    db.session.commit()
    print("Status normalization done.")
