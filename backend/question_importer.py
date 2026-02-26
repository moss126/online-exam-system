import pandas as pd
from models import db, Question, Category
from sqlalchemy.orm import load_only

# 中文模板列
CN_COLUMNS = [
    "题干",          # 必填
    "题型",          # 必填：单选题 / 多选题 / 判断题
    "分类",          # 可选：不存在会自动创建
    "选项A", "选项B", "选项C", "选项D",  # 可按需增减
    "正确答案",      # 单选：A；多选：A,C；判断：对/错/True/False
]

# 中英文列名映射（为兼容旧模板）
COLUMN_ALIASES = {
    "question_text": "题干",
    "question_type": "题型",
    "category": "分类",
    "option_A": "选项A",
    "option_B": "选项B",
    "option_C": "选项C",
    "option_D": "选项D",
    "correct_answer": "正确答案",
}

TYPE_MAP_IN = {
    "单选题": "single",
    "多选题": "multiple",
    "判断题": "true_false",
    "single": "single",
    "multiple": "multiple",
    "true_false": "true_false",
    "判断": "true_false",
}

def export_template(path: str):
    """导出中文模板，并包含三种题型示例"""
    df = pd.DataFrame(columns=CN_COLUMNS)
    # 示例：单选题
    row1 = {
        "题干": "Python是什么类型的编程语言？",
        "题型": "单选题",
        "分类": "基础",
        "选项A": "解释型",
        "选项B": "编译型",
        "选项C": "标记型",
        "选项D": "脚本型（仅）",
        "正确答案": "A",
    }
    # 示例：多选题
    row2 = {
        "题干": "以下哪些是Python的Web框架？",
        "题型": "多选题",
        "分类": "框架",
        "选项A": "Django",
        "选项B": "Flask",
        "选项C": "React",
        "选项D": "FastAPI",
        "正确答案": "A,B,D",
    }
    # 示例：判断题
    row3 = {
        "题干": "Python列表是可变（mutable）对象。",
        "题型": "判断题",
        "分类": "基础",
        "选项A": "",
        "选项B": "",
        "选项C": "",
        "选项D": "",
        "正确答案": "对",  # 也可填 True/False / 对/错
    }
    df = pd.concat([df, pd.DataFrame([row1, row2, row3])], ignore_index=True)
    df.to_excel(path, index=False)

def _cn(df, key):
    """取兼容列名：优先中文，其次英文别名"""
    if key in df.columns:
        return df[key]
    # key 为中文优先；若传入英文（如 question_text），转成中文列名
    cn = COLUMN_ALIASES.get(key, key)
    if cn in df.columns:
        return df[cn]
    # 反向匹配：如果传中文，检查是否有英文老列
    for en, zh in COLUMN_ALIASES.items():
        if zh == key and en in df.columns:
            return df[en]
    return pd.Series([""] * len(df))

def _norm_bool(v):
    s = str(v).strip().lower()
    return s in {"true", "t", "1", "yes", "y", "是", "对", "正确"}

def import_from_excel(file_path, creator_id):
    """从Excel文件批量导入题目（支持中文模板/自动创建分类）"""
    try:
        df = pd.read_excel(file_path).fillna("")

        required_any = (_cn(df, "题干"), _cn(df, "题型"), _cn(df, "正确答案"))
        if any(series.empty for series in required_any):
            raise ValueError("Excel缺少必要列：题干 / 题型 / 正确答案")

        # 预取分类
        existing_cats = {c.name: c.id for c in db.session.query(Category).options(load_only(Category.id, Category.name)).all()}

        questions_to_add = []
        for idx in range(len(df)):
            qtext = str(_cn(df, "题干").iloc[idx]).strip()
            qtype_raw = str(_cn(df, "题型").iloc[idx]).strip()
            raw_ans  = str(_cn(df, "正确答案").iloc[idx]).strip()
            cat_name = str(_cn(df, "分类").iloc[idx]).strip()

            if not qtext or not qtype_raw or not raw_ans:
                continue

            qtype = TYPE_MAP_IN.get(qtype_raw, "").strip()
            if qtype not in {"single", "multiple", "true_false"}:
                raise ValueError(f"第{idx+2}行题型无效：{qtype_raw}（可填：单选题/多选题/判断题）")

            # 分类
            category_id = None
            if cat_name:
                if cat_name not in existing_cats:
                    new_cat = Category(name=cat_name)
                    db.session.add(new_cat)
                    db.session.flush()
                    existing_cats[cat_name] = new_cat.id
                category_id = existing_cats[cat_name]

            # 选项
            options = {}
            for key in ["选项A","选项B","选项C","选项D","选项E","选项F"]:
                if key in df.columns:
                    letter = key[-1].upper()  # A/B/C...
                    val = str(df[key].iloc[idx]).strip()
                    if val:
                        options[letter] = val

            # 答案
            if qtype == "multiple":
                correct = [x.strip().upper() for x in raw_ans.replace("，", ",").split(",") if x.strip()]
            elif qtype == "true_false":
                correct = [_norm_bool(raw_ans)]
            else:
                correct = [raw_ans.strip().upper()]

            questions_to_add.append(Question(
                creator_id=creator_id,
                category_id=category_id,
                question_text=qtext,
                question_type=qtype,
                options=options if options else None,
                correct_answer=correct
            ))

        if questions_to_add:
            db.session.add_all(questions_to_add)
            db.session.commit()
        return {"success": True, "message": f"成功导入 {len(questions_to_add)} 道题目。"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"导入失败: {str(e)}"}
