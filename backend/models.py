from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    TEACHER = 'teacher'
    STUDENT = 'student'

class ExamStatus(enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    full_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    """题目分类（用于按分类抽题）"""
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # 新增分类
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # single, multiple, true_false
    options = db.Column(db.JSON)  # {"A": "Option 1", "B": "Option 2"}
    correct_answer = db.Column(db.JSON, nullable=False)  # ["A"] or ["A", "C"] or [True]
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    creator = db.relationship('User', backref=db.backref('questions', lazy=True))
    category = db.relationship('Category', backref=db.backref('questions', lazy=True))

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(ExamStatus), default=ExamStatus.INACTIVE, nullable=False)
    is_randomized = db.Column(db.Boolean, default=False)
    switch_limit = db.Column(db.Integer, default=0)  # 0表示不限制
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    creator = db.relationship('User', backref=db.backref('exams', lazy=True))

class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=5)  # 默认每题5分

    exam = db.relationship('Exam', backref=db.backref('exam_questions', cascade="all, delete-orphan"))
    question = db.relationship('Question')

class ExamAttempt(db.Model):
    __tablename__ = 'exam_attempts'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    start_time = db.Column(db.DateTime, server_default=db.func.now())
    submit_time = db.Column(db.DateTime)
    final_score = db.Column(db.Float, nullable=False)
    switch_count = db.Column(db.Integer, default=0)

    student = db.relationship('User', backref='attempts')
    exam = db.relationship('Exam', backref='attempts')

class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('exam_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    student_answer = db.Column(db.JSON)  # ["B"] or ["A", "C"] or [True]
    is_correct = db.Column(db.Boolean, nullable=False)

    attempt = db.relationship('ExamAttempt', backref='answers')
