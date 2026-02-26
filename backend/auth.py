# backend/auth.py
# 教师账户账号密码登录；学生填写姓名+工号登录
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint("auth", __name__)

# 简易内存会话（开发环境）
SESSIONS = {}  # token -> {'role','id','name','expire'}

# —— 教师账号（示例：可换成数据库查询）——
# 你也可以把下面列表换成从数据库读取的教师表
TEACHERS = {
    # username: {password, id, name}
    "teacher": {"password": "123456", "id": 1, "name": "管理员（教师）"},
    "admin": {"password": "admin123", "id": 2, "name": "系统管理员"},
}

SESSION_TTL_MIN = 8 * 60  # 8 小时

def _new_token(payload):
    token = secrets.token_hex(16)
    payload = {**payload, "expire": datetime.utcnow() + timedelta(minutes=SESSION_TTL_MIN)}
    SESSIONS[token] = payload
    return token

def _cleanup_sessions():
    now = datetime.utcnow()
    for k, v in list(SESSIONS.items()):
        if v.get("expire") and v["expire"] < now:
            SESSIONS.pop(k, None)

def get_identity(req):
    _cleanup_sessions()
    token = req.headers.get("X-Token") or req.cookies.get("token")
    if not token: 
        return None
    info = SESSIONS.get(token)
    if not info: 
        return None
    if info["expire"] < datetime.utcnow():
        SESSIONS.pop(token, None)
        return None
    return {"token": token, **info}

@auth_bp.post("/auth/teacher/login")
def teacher_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"success": False, "message": "请输入账号和密码"}), 400

    t = TEACHERS.get(username)
    if not t or t["password"] != password:
        return jsonify({"success": False, "message": "账号或密码错误"}), 401

    token = _new_token({"role": "teacher", "id": t["id"], "name": t["name"]})
    return jsonify({"success": True, "token": token, "role": "teacher", "user": {"id": t["id"], "name": t["name"]}})

@auth_bp.post("/auth/student/login")
def student_login():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    employee_no = (data.get("employee_no") or "").strip()
    if not name or not employee_no:
        return jsonify({"success": False, "message": "请填写姓名和工号"}), 400

    token = _new_token({"role": "student", "id": employee_no, "name": name})
    return jsonify({"success": True, "token": token, "role": "student", "user": {"id": employee_no, "name": name}})

@auth_bp.post("/auth/logout")
def logout():
    token = request.headers.get("X-Token") or request.cookies.get("token")
    if token in SESSIONS:
        SESSIONS.pop(token, None)
    return jsonify({"success": True})

# 可选：用于前端检查登录态
@auth_bp.get("/auth/me")
def whoami():
    me = get_identity(request)
    if not me:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "role": me["role"], "user": {"id": me["id"], "name": me["name"]}})
