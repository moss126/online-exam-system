#!/usr/bin/env python3
"""
示例数据生成脚本
用于向数据库中添加测试题目和用户数据
"""

from app import app, db
from models import User, Question, Exam, ExamQuestion
import json

def create_sample_data():
    with app.app_context():
        # 创建数据库表
        db.create_all()
        
        # 创建示例用户
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                full_name='系统管理员',
                role='TEACHER'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        if not User.query.filter_by(username='student01').first():
            student = User(
                username='student01',
                full_name='张三',
                role='STUDENT'
            )
            student.set_password('123456')
            db.session.add(student)
        
        # 创建示例题目
        sample_questions = [
            {
                'question_text': 'Python是什么类型的编程语言？',
                'question_type': 'single',
                'options': {
                    'A': '编译型语言',
                    'B': '解释型语言',
                    'C': '汇编语言',
                    'D': '机器语言'
                },
                'correct_answer': 'B'
            },
            {
                'question_text': '以下哪些是Python的Web框架？',
                'question_type': 'multiple',
                'options': {
                    'A': 'Django',
                    'B': 'Flask',
                    'C': 'Spring',
                    'D': 'FastAPI'
                },
                'correct_answer': 'A,B,D'
            },
            {
                'question_text': 'Python是一种面向对象的编程语言。',
                'question_type': 'true_false',
                'options': {},
                'correct_answer': 'True'
            },
            {
                'question_text': '在Python中，哪个关键字用于定义函数？',
                'question_type': 'single',
                'options': {
                    'A': 'function',
                    'B': 'def',
                    'C': 'func',
                    'D': 'define'
                },
                'correct_answer': 'B'
            },
            {
                'question_text': '以下哪些是Python的数据类型？',
                'question_type': 'multiple',
                'options': {
                    'A': 'int',
                    'B': 'str',
                    'C': 'list',
                    'D': 'dict'
                },
                'correct_answer': 'A,B,C,D'
            },
            {
                'question_text': 'Python的列表是可变的数据类型。',
                'question_type': 'true_false',
                'options': {},
                'correct_answer': 'True'
            },
            {
                'question_text': '在Python中，如何创建一个空列表？',
                'question_type': 'single',
                'options': {
                    'A': 'list()',
                    'B': '[]',
                    'C': 'new list()',
                    'D': 'A和B都可以'
                },
                'correct_answer': 'D'
            },
            {
                'question_text': '以下哪些是Python的循环语句？',
                'question_type': 'multiple',
                'options': {
                    'A': 'for',
                    'B': 'while',
                    'C': 'do-while',
                    'D': 'foreach'
                },
                'correct_answer': 'A,B'
            },
            {
                'question_text': 'Python中的字典是有序的数据结构。',
                'question_type': 'true_false',
                'options': {},
                'correct_answer': 'True'
            },
            {
                'question_text': '在Python中，哪个运算符用于幂运算？',
                'question_type': 'single',
                'options': {
                    'A': '^',
                    'B': '**',
                    'C': 'pow',
                    'D': 'B和C都可以'
                },
                'correct_answer': 'D'
            }
        ]
        
        # 获取管理员用户作为题目创建者
        admin_user = User.query.filter_by(username='admin').first()
        
        # 添加题目到数据库
        for q_data in sample_questions:
            existing_question = Question.query.filter_by(question_text=q_data['question_text']).first()
            if not existing_question:
                question = Question(
                    creator_id=admin_user.id,
                    question_text=q_data['question_text'],
                    question_type=q_data['question_type'],
                    options=json.dumps(q_data['options']) if q_data['options'] else None,
                    correct_answer=q_data['correct_answer']
                )
                db.session.add(question)
        
        # 提交所有更改
        db.session.commit()
        print("示例数据创建成功！")
        print(f"用户数量: {User.query.count()}")
        print(f"题目数量: {Question.query.count()}")

if __name__ == '__main__':
    create_sample_data()
