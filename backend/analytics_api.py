# backend/analytics_api.py
from flask import Blueprint, jsonify
from sqlalchemy import func
from datetime import datetime
from models import db, Exam, ExamAttempt, StudentAnswer, Question

analytics_bp = Blueprint("analytics_api", __name__)

@analytics_bp.get("/analytics/teacher/overview")
def teacher_overview():
    total_exams = db.session.query(func.count(Exam.id)).scalar() or 0
    total_participants = db.session.query(func.count(func.distinct(ExamAttempt.student_id))).scalar() or 0
    avg_score = float(db.session.query(func.coalesce(func.avg(ExamAttempt.final_score), 0)).scalar() or 0)
    max_score = float(db.session.query(func.coalesce(func.max(ExamAttempt.final_score), 0)).scalar() or 0)

    ranges = [(0,59), (60,69), (70,79), (80,89), (90,100)]
    buckets = []
    for lo, hi in ranges:
        cnt = db.session.query(func.count(ExamAttempt.id))\
            .filter(ExamAttempt.final_score >= lo, ExamAttempt.final_score <= hi).scalar() or 0
        buckets.append({"range": f"{lo}-{hi}", "count": int(cnt)})

    exams = db.session.query(Exam).order_by(Exam.id.desc()).all()
    exam_rows = []
    for e in exams:
        q = db.session.query(
            func.count(ExamAttempt.id),
            func.coalesce(func.avg(ExamAttempt.final_score), 0),
            func.coalesce(func.max(ExamAttempt.final_score), 0),
        ).filter(ExamAttempt.exam_id == e.id).one()
        exam_rows.append({
            "id": e.id,
            "title": e.title,
            "attempts": int(q[0] or 0),
            "avg_score": float(q[1] or 0),
            "max_score": float(q[2] or 0),
        })

    return jsonify({
        "success": True,
        "data": {
            "total_exams": int(total_exams),
            "total_participants": int(total_participants),
            "avg_score": round(avg_score, 1),
            "max_score": int(max_score),
            "score_buckets": buckets,
            "exams": exam_rows
        }
    })

# 提交明细：学生姓名 + 工号（从 ExamAttempt.student_name / employee_no 字段读取，若不存在安全回退）
@analytics_bp.get("/analytics/exam/<int:exam_id>/submissions")
def exam_submissions(exam_id: int):
    exam = Exam.query.get(exam_id)
    if not exam:
        return jsonify({"success": False, "message": "考试不存在"}), 404

    attempts = ExamAttempt.query.filter_by(exam_id=exam_id)\
        .order_by(ExamAttempt.submit_time.desc().nullslast()).all()

    out = []
    for a in attempts:
        out.append({
            "attempt_id": a.id,
            "student_id": a.student_id,  # 兼容旧字段
            "student_name": getattr(a, "student_name", None) or "",   # 新增显示：学生姓名
            "employee_no": getattr(a, "employee_no", None) or "",     # 新增显示：工号
            "final_score": float(a.final_score or 0),
            "submit_time": (a.submit_time.isoformat(timespec="seconds") if isinstance(a.submit_time, datetime) else None),
            "switch_count": int(a.switch_count or 0),
        })

    return jsonify({"success": True, "exam": {"id": exam.id, "title": exam.title}, "submissions": out})

# 单份提交的“答题明细”
@analytics_bp.get("/analytics/attempt/<int:attempt_id>/answers")
def attempt_answers(attempt_id: int):
    attempt = ExamAttempt.query.get(attempt_id)
    if not attempt:
        return jsonify({"success": False, "message": "提交不存在"}), 404

    q_map = {q.id: q for q in Question.query.all()}
    rows = StudentAnswer.query.filter_by(attempt_id=attempt_id).all()
    items = []
    for ans in rows:
        q = q_map.get(ans.question_id)
        items.append({
            "question_id": ans.question_id,
            "question_text": (q.question_text if q else ""),
            "question_type": (q.question_type if q else ""),
            "options": (q.options if q else None),
            "correct_answer": (q.correct_answer if q else None),
            "student_answer": ans.student_answer,
            "is_correct": bool(ans.is_correct),
            "score": getattr(ans, "score", None),
        })

    return jsonify({
        "success": True,
        "attempt": {
            "id": attempt.id,
            "exam_id": attempt.exam_id,
            "student_id": attempt.student_id,
            "student_name": getattr(attempt, "student_name", None) or "",
            "employee_no": getattr(attempt, "employee_no", None) or "",
            "final_score": float(attempt.final_score or 0),
            "submit_time": (attempt.submit_time.isoformat(timespec="seconds") if isinstance(attempt.submit_time, datetime) else None),
        },
        "answers": items
    })
