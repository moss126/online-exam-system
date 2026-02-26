# backend/exam_api.py
from datetime import datetime
import random
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from models import (
    db,
    Exam,
    ExamStatus,
    Question,
    Category,
    ExamAttempt,
    StudentAnswer,
)

# 可选：试卷与题目的关联模型，不存在时自动降级
try:
    from models import ExamQuestion  # 字段建议：id, exam_id, question_id, score
except Exception:  # noqa
    ExamQuestion = None

# 可选：外部批量更新函数，不存在时使用内置实现
try:
    from exam_manager import update_exam_questions as _update_exam_questions
except Exception:  # noqa
    _update_exam_questions = None

# 可选：读取登录身份（用于教师创建、学生提交）
try:
    from auth import get_identity
except Exception:  # noqa
    def get_identity(_req):  # 兜底：未集成鉴权时返回空
        return {}

exam_bp = Blueprint("exam_api", __name__)


# ---------------- 工具函数 ----------------
def _is_active(exam: Exam) -> bool:
    """试卷是否已发布（ACTIVE）"""
    status = getattr(exam, "status", None)
    name = getattr(status, "name", None) if status is not None else None
    # 兼容：若直接把枚举值存到 Exam.status
    if name is None and isinstance(getattr(exam, "status", None), (str, int)):
        return getattr(exam, "status") == getattr(ExamStatus, "ACTIVE", "ACTIVE")
    return bool(name == "ACTIVE")


def _attach_questions_replace(exam_id: int, qids: list[int], score_each: int):
    """用传入的 qids 全量替换试卷题目（需要 ExamQuestion；若无则跳过）"""
    if ExamQuestion is None:
        return
    db.session.query(ExamQuestion).filter(
        ExamQuestion.exam_id == exam_id
    ).delete(synchronize_session=False)
    rows = [
        ExamQuestion(exam_id=exam_id, question_id=int(qid), score=score_each)
        for qid in qids
    ]
    if rows:
        db.session.add_all(rows)


def _pick_by_random_config(cfg: dict) -> list[int]:
    """
    cfg 结构：
    {
      single:   { total, byCategory: {'基础':2,'语法':3} },
      multiple: { total, byCategory: {...} },
      true_false:{ total, byCategory: {...} }
    }
    规则：先满足 byCategory；不足则从该题型剩余里随机补足 total。
    """
    cats = {c.name: c.id for c in Category.query.all()}
    picked: list[int] = []

    def pick_for_type(qtype: str, tc: dict):
        nonlocal picked
        tc = tc or {}
        total_target = int(tc.get("total") or 0)
        by_cat = tc.get("byCategory") or {}

        got = []
        # 先按分类拿
        for cname, need in (by_cat or {}).items():
            cid = cats.get(cname)
            if not cid:
                continue
            pool = [
                r.id
                for r in Question.query.with_entities(Question.id)
                .filter(Question.question_type == qtype, Question.category_id == cid)
                .all()
                if r.id not in picked and r.id not in got
            ]
            random.shuffle(pool)
            got.extend(pool[: int(need or 0)])

        # 补齐到 total
        if total_target > len(got):
            remain = total_target - len(got)
            pool = [
                r.id
                for r in Question.query.with_entities(Question.id)
                .filter(Question.question_type == qtype)
                .all()
                if r.id not in picked and r.id not in got
            ]
            random.shuffle(pool)
            got.extend(pool[:remain])

        picked.extend(got)

    for t in ("single", "multiple", "true_false"):
        if t in (cfg or {}):
            pick_for_type(t, (cfg or {}).get(t))

    return picked


# ---------------- 教师端：考试列表（修复 /api/teacher/exams 404） ----------------
@exam_bp.get("/teacher/exams")
def list_teacher_exams():
    exams = Exam.query.order_by(Exam.id.desc()).all()
    out = []
    for e in exams:
        out.append(
            {
                "id": e.id,
                "title": e.title,
                "duration_minutes": int(getattr(e, "duration_minutes", 60) or 60),
                "is_open": _is_active(e),
            }
        )
    return jsonify({"success": True, "exams": out})


# ---------------- 学生端：仅返回已发布 ----------------
@exam_bp.get("/student/exams")
def list_student_exams():
    try:
        exams = (
            Exam.query.filter(Exam.status == ExamStatus.ACTIVE)
            .order_by(Exam.id.desc())
            .all()
        )
    except Exception:
        exams = [e for e in Exam.query.order_by(Exam.id.desc()).all() if _is_active(e)]
    out = [
        {
            "id": e.id,
            "title": e.title,
            "duration_minutes": int(getattr(e, "duration_minutes", 60) or 60),
        }
        for e in exams
    ]
    return jsonify({"success": True, "exams": out})


# ---------------- 教师端：创建考试（支持预检 OPTIONS） ----------------
@exam_bp.route("/exams", methods=["POST", "OPTIONS"])
def create_exam():
    if request.method == "OPTIONS":
        return ("", 204)

    # 必须教师登录，写入 creator_id（避免 NOT NULL 失败）
    ident = get_identity(request) or {}
    if ident.get("role") != "teacher":
        return jsonify({"success": False, "message": "请先以教师身份登录"}), 401
    try:
        creator_id = int(ident.get("id"))
    except Exception:
        return jsonify({"success": False, "message": "教师身份无效"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    duration = int(data.get("durationMinutes") or 60)
    is_randomized = bool(data.get("isRandomized", True))
    switch_limit = int(data.get("switchLimit") or 0)
    default_score = int(data.get("defaultScore") or 1)
    if not title:
        return jsonify({"success": False, "message": "考试名称不能为空"}), 400

    exam = Exam(creator_id=creator_id, title=title)
    if hasattr(exam, "duration_minutes"):
        exam.duration_minutes = duration
    if hasattr(exam, "is_randomized"):
        exam.is_randomized = is_randomized
    if hasattr(exam, "switch_limit"):
        exam.switch_limit = switch_limit
    try:
        exam.status = getattr(ExamStatus, "INACTIVE", "INACTIVE")
    except Exception:
        pass

    db.session.add(exam)
    db.session.flush()  # 获取 exam.id

    question_ids = data.get("question_ids")
    random_cfg = data.get("random_config")
    try:
        if question_ids:
            _attach_questions_replace(
                exam.id, list(map(int, question_ids)), default_score
            )
        elif random_cfg:
            picked = _pick_by_random_config(random_cfg)
            _attach_questions_replace(exam.id, picked, default_score)
        # 允许空卷（无题目）
        db.session.commit()
        return jsonify({"success": True, "id": exam.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"创建失败：{e}"}), 500


# ---------------- 教师端：发布/取消发布 ----------------
@exam_bp.post("/exam/<int:exam_id>/toggle")
def toggle_exam(exam_id: int):
    exam = Exam.query.get(exam_id)
    if not exam:
        return jsonify({"success": False, "message": "考试不存在"}), 404
    try:
        if _is_active(exam):
            exam.status = getattr(ExamStatus, "INACTIVE", "INACTIVE")
        else:
            exam.status = getattr(ExamStatus, "ACTIVE", "ACTIVE")
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"更新状态失败：{e}"}), 500


# ---------------- 教师端：替换题目/批量分值 ----------------
@exam_bp.post("/exam/<int:exam_id>/questions")
def api_update_exam_questions(exam_id: int):
    data = request.get_json(silent=True) or {}
    if _update_exam_questions:
        result = _update_exam_questions(
            exam_id, data.get("updates") or {}, data.get("defaultScore")
        )
        return (jsonify(result), 200 if result.get("success") else 400)

    if ExamQuestion is None:
        return jsonify({"success": False, "message": "未实现题目关联模型 ExamQuestion"}), 501

    updates = data.get("updates") or {}
    repl = updates.get("replace") or []
    score_each = int(data.get("defaultScore") or 1)
    try:
        _attach_questions_replace(exam_id, list(map(int, repl)), score_each)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"更新失败：{e}"}), 500


# ---------------- 获取试卷详情（仅已发布；支持预检 OPTIONS） ----------------
@exam_bp.route("/exam/<int:exam_id>", methods=["GET", "OPTIONS"])
def get_exam_detail(exam_id: int):
    if request.method == "OPTIONS":
        return ("", 204)

    exam = Exam.query.get(exam_id)
    if not exam or not _is_active(exam):
        return jsonify({"success": False, "message": "试卷不存在或未发布"}), 404

    q_list = []
    if ExamQuestion is not None:
        rows = (
            db.session.query(Question, ExamQuestion)
            .join(ExamQuestion, ExamQuestion.question_id == Question.id)
            .filter(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.id.asc())
            .all()
        )
        for q, rel in rows:
            q_list.append(
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": q.options or {},
                    "score": getattr(rel, "score", None),
                }
            )
    else:
        # 降级：没有关联表就按 exam.questions 或全库返回（不含正确答案）
        rels = getattr(exam, "questions", None)
        if rels is not None:
            for q in rels:
                q_list.append(
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "options": q.options or {},
                        "score": getattr(q, "score", None),
                    }
                )
        else:
            for q in Question.query.order_by(Question.id.asc()).all():
                q_list.append(
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "options": q.options or {},
                        "score": getattr(q, "score", None),
                    }
                )

    return jsonify(
        {
            "success": True,
            "exam": {
                "id": exam.id,
                "title": exam.title,
                "duration_minutes": int(getattr(exam, "duration_minutes", 60) or 60),
            },
            "questions": q_list,
        }
    )


# ---------------- 学生提交：不限制设备；同名仅一次 ----------------
@exam_bp.post("/exam/<int:exam_id>/submit")
def submit_exam(exam_id: int):
    exam = Exam.query.get(exam_id)
    if not exam or not _is_active(exam):
        return jsonify({"success": False, "message": "考试未发布或不存在"}), 400

    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers") or []
    switch_count = int(payload.get("switch_count") or 0)

    ident = get_identity(request) or {}
    student_name = (payload.get("student_name") or ident.get("name") or "").strip()
    employee_no = (payload.get("employee_no") or ident.get("id") or "").strip()
    if not student_name:
        return jsonify({"success": False, "message": "缺少学生姓名"}), 400

    existed = (
        ExamAttempt.query.filter(
            ExamAttempt.exam_id == exam_id,
            func.trim(ExamAttempt.student_name) == student_name,
        ).first()
        is not None
    )
    if existed:
        return jsonify({"success": False, "message": "该姓名已提交，不可重复提交"}), 409

    # 判分
    q_map = {q.id: q for q in Question.query.all()}
    total_score = 0.0
    answer_rows = []

    def _norm(v):
        if isinstance(v, list):
            return [str(x).strip().upper() for x in v]
        if isinstance(v, bool):
            return [v]
        return [str(v).strip().upper()]

    for item in answers:
        qid = int(item.get("question_id"))
        stu_ans = item.get("answer")
        q = q_map.get(qid)
        correct = False
        if q:
            ca = _norm(q.correct_answer)
            sa = _norm(stu_ans)
            try:
                correct = sorted(ca) == sorted(sa)
            except Exception:
                correct = ca == sa
            per_score = getattr(q, "score", 1)
            if correct:
                total_score += float(per_score)
        answer_rows.append((qid, stu_ans, correct))

    try:
        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=employee_no or None,  # 兼容旧字段
            student_name=student_name,
            employee_no=employee_no or None,
            final_score=total_score,
            submit_time=datetime.utcnow(),
            switch_count=switch_count,
        )
        db.session.add(attempt)
        db.session.flush()

        for qid, stu_ans, ok in answer_rows:
            db.session.add(
                StudentAnswer(
                    attempt_id=attempt.id,
                    question_id=qid,
                    student_answer=stu_ans,
                    is_correct=ok,
                )
            )

        db.session.commit()
        return jsonify({"success": True, "attempt_id": attempt.id, "score": total_score})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"提交失败：{e}"}), 500
