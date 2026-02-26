# backend/app.py  （在你当前基础上补注册 qbank_bp，其余保持一致）
import os
from flask import Flask
from flask_cors import CORS

from models import db
from auth import auth_bp
from analytics_api import analytics_bp
from exam_api import exam_bp
from question_api import qbank_bp   # 新增：题库与分类 API

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Token"],
    expose_headers=["Content-Type"],
)

app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{os.path.join(BASE_DIR, 'exam_system.db')}")
app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
app.config.setdefault("JSON_AS_ASCII", False)

db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(auth_bp, url_prefix="/api")
app.register_blueprint(exam_bp, url_prefix="/api")
app.register_blueprint(analytics_bp, url_prefix="/api")
app.register_blueprint(qbank_bp, url_prefix="/api")   # 新增注册

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
