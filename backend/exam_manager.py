from models import db, Exam, Question, ExamQuestion, ExamStatus, ExamAttempt, StudentAnswer, Category
from sqlalchemy.sql.expression import func
from datetime import datetime
import random, json

# ================== 工具函数 ==================

def _load_json_like(data):
    if data is None:
        return {}
    if isinstance(data, (dict, list, bool)):
        return data
    s = str(data).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    parts = [p.strip() for p in s.replace("；", ";").replace("，", ",").replace(" ", ",").split(",") if p.strip()]
    return parts

def _normalize_options(options):
    """统一成 dict: {'A': 'xxx', 'B': 'yyy'}"""
    data = _load_json_like(options)
    if isinstance(data, dict):
        # 保持键大写
        return {str(k).upper(): v for k, v in data.items()}
    if isinstance(data, list):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return {letters[i]: v for i, v in enumerate(data)}
    return {}

def _normalize_answer(ans):
    """把正确答案统一成可比对格式（list[str]|[bool]|str|bool）"""
    data = _load_json_like(ans)
    # 直接透传 bool
    if isinstance(data, bool):
        return data
    if isinstance(data, str):
        s = data.strip().upper()
        if s in {"TRUE", "T", "YES", "正确", "对", "1"}:
            return True
        if s in {"FALSE", "F", "NO", "错误", "错", "0"}:
            return False
        if "," in s:
            return [x.strip().upper() for x in s.split(",") if x.strip()]
        return s  # 单选: 'A'
    if isinstance(data, list):
        # 可能是 ["A","C"] 或 [True]
        if len(data) == 1 and isinstance(data[0], bool):
            return data[0]
        return [str(x).strip().upper() if not isinstance(x, bool) else x for x in data]
    if isinstance(data, dict):
        return [str(k).strip().upper() for k, v in data.items() if v]
    return data

# ================== 创建/编辑考试 ==================

def create_exam(data, creator_id):
    """创建一场新考试（支持按分类随机抽题）"""
    try:
        new_exam = Exam(
            creator_id=creator_id,
            title=data['title'],
            start_time=datetime.utcnow() if not data.get('startTime') else datetime.fromisoformat(data['startTime']),
            end_time=datetime.utcnow() if not data.get('endTime') else datetime.fromisoformat(data['endTime']),
            duration_minutes=data['durationMinutes'],
            status=ExamStatus.INACTIVE,
            is_randomized=data.get('isRandomized', False),
            switch_limit=data.get('switchLimit', 0)
        )
        db.session.add(new_exam)
        db.session.flush()  # 拿到 exam.id

        default_score = int(data.get('defaultScore', 5) or 5)

        # 组卷
        if 'random_config' in data:
            # random_config 示例：
            # {
            #   "single": { "total": 5, "byCategory": {"基础":2, "语法":3} },
            #   "multiple": { "total": 3 },
            #   "true_false": { "total": 2, "byCategory": {"判断":2} }
            # }
            config = data['random_config'] or {}
            for q_type, conf in config.items():
                total = int(conf.get("total", 0))
                by_cat = conf.get("byCategory") or {}
                picked = []

                # 先按分类抽
                for cat_name, need in by_cat.items():
                    cat = Category.query.filter_by(name=cat_name).first()
                    if not cat:
                        raise ValueError(f"分类 '{cat_name}' 不存在")
                    qs = (
                        Question.query
                        .filter_by(question_type=q_type, category_id=cat.id, creator_id=creator_id)
                        .order_by(func.random())
                        .limit(int(need))
                        .all()
                    )
                    if len(qs) < int(need):
                        raise ValueError(f"分类'{cat_name}'中'{q_type}'不足 {need} 道")
                    picked.extend(qs)

                # 再补齐到 total
                remain = max(0, total - len(picked))
                if remain > 0:
                    extra = (
                        Question.query
                        .filter_by(question_type=q_type, creator_id=creator_id)
                        .filter(~Question.id.in_([q.id for q in picked]))
                        .order_by(func.random()).limit(remain).all()
                    )
                    if len(extra) < remain:
                        raise ValueError(f"题库中'{q_type}'题目不足 {total} 道")
                    picked.extend(extra)

                for q in picked:
                    db.session.add(ExamQuestion(
                        exam_id=new_exam.id,
                        question_id=q.id,
                        score=default_score
                    ))
        elif 'question_ids' in data:
            for q_id in data['question_ids']:
                db.session.add(ExamQuestion(
                    exam_id=new_exam.id,
                    question_id=q_id,
                    score=default_score
                ))

        db.session.commit()
        return {"success": True, "message": "考试创建成功", "exam_id": new_exam.id}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}

def update_exam_questions(exam_id, updates, defaultScore=None):
    """
    编辑已创建试卷题目：
    updates = {
      "add": [qid,...],
      "remove": [qid,...],
      "replace": [qid,...]  # 可选：先清空后全量加入
    }
    defaultScore: 批量设置默认分值（可选）
    """
    try:
        exam = Exam.query.get(exam_id)
        if not exam:
            return {"success": False, "message": "考试不存在"}

        if updates.get("replace"):
            ExamQuestion.query.filter_by(exam_id=exam_id).delete(synchronize_session=False)
            for qid in updates["replace"]:
                db.session.add(ExamQuestion(exam_id=exam_id, question_id=qid, score=int(defaultScore or 5)))
        else:
            if updates.get("remove"):
                ExamQuestion.query.filter(ExamQuestion.exam_id==exam_id, ExamQuestion.question_id.in_(updates["remove"])).delete(synchronize_session=False)
            if updates.get("add"):
                for qid in updates["add"]:
                    db.session.add(ExamQuestion(exam_id=exam_id, question_id=qid, score=int(defaultScore or 5)))

        if defaultScore is not None and not updates.get("replace"):
            # 批量设置（存在的全部改为 defaultScore）
            db.session.query(ExamQuestion).filter_by(exam_id=exam_id).update({"score": int(defaultScore)}, synchronize_session=False)

        db.session.commit()
        return {"success": True, "message": "试卷题目已更新"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}

# ================== 学生端试卷视图 ==================

def get_exam_for_student(exam_id):
    """返回给学生答题的试卷（保证 options 始终为 dict，避免前端判分错配）"""
    exam = Exam.query.get(exam_id)
    if not exam:
        return {"success": False, "message": "考试不存在"}
    if exam.status != ExamStatus.ACTIVE:
        return {"success": False, "message": "考试未开放"}

    exam_questions = ExamQuestion.query.filter_by(exam_id=exam_id).all()
    questions = [eq.question for eq in exam_questions]

    if exam.is_randomized:
        random.shuffle(questions)

    q_list = []
    for q in questions:
        opts = _normalize_options(q.options)
        # 如需乱序，打乱键顺序后再重建 dict（保持是 dict）
        if exam.is_randomized and len(opts) > 1:
            items = list(opts.items())
            random.shuffle(items)
            opts = {k: v for k, v in items}

        q_list.append({
            "id": q.id,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": opts  # 始终返回 dict
        })

    return {
        "success": True,
        "exam": {
            "id": exam.id,
            "title": exam.title,
            "duration_minutes": exam.duration_minutes,
            "switch_limit": exam.switch_limit,
            "questions": q_list
        }
    }

# ================== 提交判分（更健壮） ==================

def submit_and_grade_exam(exam_id, student_id, answers_data):
    """接收答案并判分（修复各种格式导致的误判）"""
    try:
        # 防止重复提交
        if ExamAttempt.query.filter_by(student_id=student_id, exam_id=exam_id).first():
            return {"success": False, "message": "您已提交过"}

        exam_questions = ExamQuestion.query.filter_by(exam_id=exam_id).all()
        q_map = {eq.question_id: (eq.question, eq.score) for eq in exam_questions}
        total = 0

        attempt = ExamAttempt(
            student_id=student_id,
            exam_id=exam_id,
            submit_time=datetime.utcnow(),
            switch_count=answers_data.get('switchCount', 0),
            final_score=0
        )
        db.session.add(attempt)
        db.session.flush()

        # 兼容：answers 的 key 可能是 int 或 str
        answers = answers_data.get('answers', {}) or {}
        normalized_answers = {}
        for k, v in answers.items():
            try:
                normalized_answers[int(k)] = v
            except Exception:
                continue

        for qid, (question, score) in q_map.items():
            if qid not in normalized_answers:
                stu_ans = [] if question.question_type == 'multiple' else None
            else:
                stu_ans = normalized_answers[qid]

            correct = _normalize_answer(question.correct_answer)

            # 统一学生答案格式
            if question.question_type == 'true_false':
                # 允许 True/False / "true"/"false" / ["True"] / [True]
                if isinstance(stu_ans, list) and len(stu_ans) == 1:
                    stu = _normalize_answer(stu_ans[0])
                else:
                    stu = _normalize_answer(stu_ans)
                is_correct = (stu == correct)
            else:
                # 单/多选：统一成大写列表
                if stu_ans is None or stu_ans == '':
                    stu_list = []
                elif isinstance(stu_ans, list):
                    stu_list = [str(x).strip().upper() for x in stu_ans]
                else:
                    stu_list = [str(stu_ans).strip().upper()]
                corr_list = correct if isinstance(correct, list) else [str(correct).strip().upper()]
                is_correct = sorted(stu_list) == sorted(corr_list)

            if is_correct:
                total += score

            db.session.add(StudentAnswer(
                attempt_id=attempt.id,
                question_id=qid,
                student_answer=stu_ans if isinstance(stu_ans, list) else [stu_ans] if stu_ans not in (None, '') else [],
                is_correct=bool(is_correct)
            ))

        attempt.final_score = total
        db.session.commit()
        return {"success": True, "message": "交卷成功", "score": total}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"提交失败: {str(e)}"}
