# backend/question_api.py
from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import func
from io import BytesIO
import tempfile
import os

from models import db, Question, Category
from question_importer import import_from_excel, export_template

qbank_bp = Blueprint("qbank_api", __name__)

# ---------- Categories ----------
@qbank_bp.get("/categories")
def list_categories():
    rows = Category.query.order_by(Category.id.asc()).all()
    return jsonify({"success": True, "categories": [{"id": c.id, "name": c.name} for c in rows]})

@qbank_bp.post("/categories")
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "分类名不能为空"}), 400
    existed = Category.query.filter(func.lower(Category.name) == name.lower()).first()
    if existed:
        return jsonify({"success": False, "message": "分类已存在"}), 409
    c = Category(name=name)
    db.session.add(c)
    db.session.commit()
    return jsonify({"success": True, "id": c.id})

# ---------- Questions ----------
@qbank_bp.get("/questions")
def list_questions():
    # 返回题库，附带分类名
    rows = db.session.query(Question, Category).outerjoin(Category, Question.category_id == Category.id)\
        .order_by(Question.id.asc()).all()
    out = []
    for q, c in rows:
        out.append({
            "id": q.id,
            "creator_id": q.creator_id,
            "category_id": q.category_id,
            "category_name": getattr(c, "name", None),
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "created_at": getattr(q, "created_at", None).isoformat() if getattr(q, "created_at", None) else None
        })
    return jsonify({"success": True, "questions": out})

@qbank_bp.post("/questions")
def create_question():
    data = request.get_json(silent=True) or {}
    q = Question(
        creator_id=data.get("creator_id"),
        category_id=data.get("category_id"),
        question_text=(data.get("question_text") or "").strip(),
        question_type=data.get("question_type") or "single",
        options=data.get("options"),
        correct_answer=data.get("correct_answer"),
    )
    if not q.question_text:
        return jsonify({"success": False, "message": "题干不能为空"}), 400
    db.session.add(q)
    db.session.commit()
    return jsonify({"success": True, "id": q.id})

@qbank_bp.put("/questions/<int:qid>")
def update_question(qid: int):
    q = Question.query.get(qid)
    if not q:
        return jsonify({"success": False, "message": "题目不存在"}), 404
    data = request.get_json(silent=True) or {}
    if "question_text" in data:
        q.question_text = (data.get("question_text") or "").strip()
    if "question_type" in data:
        q.question_type = data.get("question_type") or q.question_type
    if "category_id" in data:
        q.category_id = data.get("category_id")
    if "options" in data:
        q.options = data.get("options")
    if "correct_answer" in data:
        q.correct_answer = data.get("correct_answer")
    db.session.commit()
    return jsonify({"success": True})

@qbank_bp.delete("/questions/<int:qid>")
def delete_question(qid: int):
    q = Question.query.get(qid)
    if not q:
        return jsonify({"success": False, "message": "题目不存在"}), 404
    db.session.delete(q)
    db.session.commit()
    return jsonify({"success": True})

# ---------- Excel 导入 / 模板 ----------
@qbank_bp.post("/questions/upload")
def upload_questions_excel():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "未选择文件"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"success": False, "message": "未选择文件"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.filename)[1] or ".xlsx") as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name
    try:
        # 这里可从登录态取 creator_id；没有则置 None
        creator_id = None
        result = import_from_excel(tmp_path, creator_id)
        code = 200 if result.get("success") else 400
        return jsonify(result), code
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@qbank_bp.get("/questions/template")
def download_template():
    # 生成一个内存文件返回
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        path = tmp.name
    try:
        export_template(path)
        return send_file(path, as_attachment=True, download_name="题库导入模板.xlsx")
    finally:
        # send_file 结束后再清理，由于 send_file 可能在 WSGI 层处理，这里不立即删除
        pass
