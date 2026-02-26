"""
数据统计分析模块
提供考试结果的统计分析功能
"""

from flask import Blueprint, jsonify, request
from models import db, Exam, Question, User
from sqlalchemy import func, text
import json

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/exam/<int:exam_id>/stats', methods=['GET'])
def get_exam_statistics(exam_id):
    """获取考试统计数据"""
    try:
        exam = Exam.query.get_or_404(exam_id)
        
        # 基础统计
        total_participants = db.session.execute(
            text("SELECT COUNT(DISTINCT user_id) FROM exam_results WHERE exam_id = :exam_id"),
            {"exam_id": exam_id}
        ).scalar() or 0
        
        # 分数统计
        score_stats = db.session.execute(
            text("""
                SELECT 
                    AVG(score) as avg_score,
                    MIN(score) as min_score,
                    MAX(score) as max_score,
                    COUNT(*) as total_submissions
                FROM exam_results 
                WHERE exam_id = :exam_id
            """),
            {"exam_id": exam_id}
        ).fetchone()
        
        # 分数分布
        score_distribution = db.session.execute(
            text("""
                SELECT 
                    CASE 
                        WHEN score >= 90 THEN '优秀(90-100)'
                        WHEN score >= 80 THEN '良好(80-89)'
                        WHEN score >= 70 THEN '中等(70-79)'
                        WHEN score >= 60 THEN '及格(60-69)'
                        ELSE '不及格(0-59)'
                    END as grade_range,
                    COUNT(*) as count
                FROM exam_results 
                WHERE exam_id = :exam_id
                GROUP BY 
                    CASE 
                        WHEN score >= 90 THEN '优秀(90-100)'
                        WHEN score >= 80 THEN '良好(80-89)'
                        WHEN score >= 70 THEN '中等(70-79)'
                        WHEN score >= 60 THEN '及格(60-69)'
                        ELSE '不及格(0-59)'
                    END
                ORDER BY MIN(score) DESC
            """),
            {"exam_id": exam_id}
        ).fetchall()
        
        # 题目正确率统计
        question_stats = db.session.execute(
            text("""
                SELECT 
                    q.id,
                    q.question_text,
                    q.question_type,
                    COUNT(CASE WHEN era.is_correct = 1 THEN 1 END) as correct_count,
                    COUNT(*) as total_count,
                    ROUND(COUNT(CASE WHEN era.is_correct = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as accuracy_rate
                FROM questions q
                JOIN exam_questions eq ON q.id = eq.question_id
                LEFT JOIN exam_result_answers era ON q.id = era.question_id
                LEFT JOIN exam_results er ON era.exam_result_id = er.id
                WHERE eq.exam_id = :exam_id AND (er.exam_id = :exam_id OR er.exam_id IS NULL)
                GROUP BY q.id, q.question_text, q.question_type
                ORDER BY accuracy_rate ASC
            """),
            {"exam_id": exam_id}
        ).fetchall()
        
        return jsonify({
            'success': True,
            'statistics': {
                'exam_info': {
                    'title': exam.title,
                    'total_questions': len(exam.questions),
                    'duration_minutes': exam.duration_minutes
                },
                'participation': {
                    'total_participants': total_participants,
                    'total_submissions': score_stats.total_submissions if score_stats else 0
                },
                'score_summary': {
                    'average_score': round(score_stats.avg_score, 2) if score_stats and score_stats.avg_score else 0,
                    'min_score': score_stats.min_score if score_stats else 0,
                    'max_score': score_stats.max_score if score_stats else 0
                },
                'score_distribution': [
                    {'grade_range': row.grade_range, 'count': row.count}
                    for row in score_distribution
                ],
                'question_analysis': [
                    {
                        'question_id': row.id,
                        'question_text': row.question_text[:50] + '...' if len(row.question_text) > 50 else row.question_text,
                        'question_type': row.question_type,
                        'correct_count': row.correct_count,
                        'total_count': row.total_count,
                        'accuracy_rate': row.accuracy_rate
                    }
                    for row in question_stats
                ]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@analytics_bp.route('/api/analytics/teacher/overview', methods=['GET'])
def get_teacher_overview():
    """获取教师总览统计"""
    try:
        # 这里应该根据当前登录的教师ID来筛选
        # 为了演示，我们使用所有数据
        
        # 考试统计
        total_exams = Exam.query.count()
        active_exams = Exam.query.filter_by(status='active').count()
        
        # 题目统计
        total_questions = Question.query.count()
        question_types = db.session.execute(
            text("""
                SELECT question_type, COUNT(*) as count
                FROM questions
                GROUP BY question_type
            """)
        ).fetchall()
        
        # 学生参与统计
        total_students = User.query.filter_by(role='STUDENT').count()
        
        # 最近考试活动
        recent_results = db.session.execute(
            text("""
                SELECT 
                    e.title as exam_title,
                    u.full_name as student_name,
                    er.score,
                    er.submitted_at
                FROM exam_results er
                JOIN exams e ON er.exam_id = e.id
                JOIN users u ON er.user_id = u.id
                ORDER BY er.submitted_at DESC
                LIMIT 10
            """)
        ).fetchall()
        
        return jsonify({
            'success': True,
            'overview': {
                'exam_stats': {
                    'total_exams': total_exams,
                    'active_exams': active_exams,
                    'inactive_exams': total_exams - active_exams
                },
                'question_stats': {
                    'total_questions': total_questions,
                    'by_type': [
                        {'type': row.question_type, 'count': row.count}
                        for row in question_types
                    ]
                },
                'student_stats': {
                    'total_students': total_students
                },
                'recent_activity': [
                    {
                        'exam_title': row.exam_title,
                        'student_name': row.student_name,
                        'score': row.score,
                        'submitted_at': row.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if row.submitted_at else None
                    }
                    for row in recent_results
                ]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@analytics_bp.route('/api/analytics/student/<int:student_id>/performance', methods=['GET'])
def get_student_performance(student_id):
    """获取学生个人成绩分析"""
    try:
        student = User.query.get_or_404(student_id)
        
        # 学生考试历史
        exam_history = db.session.execute(
            text("""
                SELECT 
                    e.title as exam_title,
                    er.score,
                    er.submitted_at,
                    e.duration_minutes,
                    (SELECT COUNT(*) FROM exam_questions WHERE exam_id = e.id) as total_questions
                FROM exam_results er
                JOIN exams e ON er.exam_id = e.id
                WHERE er.user_id = :student_id
                ORDER BY er.submitted_at DESC
            """),
            {"student_id": student_id}
        ).fetchall()
        
        # 成绩趋势
        scores = [row.score for row in exam_history]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # 错题分析
        wrong_questions = db.session.execute(
            text("""
                SELECT 
                    q.question_text,
                    q.question_type,
                    q.correct_answer,
                    era.student_answer,
                    e.title as exam_title
                FROM exam_result_answers era
                JOIN exam_results er ON era.exam_result_id = er.id
                JOIN questions q ON era.question_id = q.id
                JOIN exams e ON er.exam_id = e.id
                WHERE er.user_id = :student_id AND era.is_correct = 0
                ORDER BY er.submitted_at DESC
                LIMIT 20
            """),
            {"student_id": student_id}
        ).fetchall()
        
        return jsonify({
            'success': True,
            'performance': {
                'student_info': {
                    'name': student.full_name,
                    'username': student.username
                },
                'summary': {
                    'total_exams': len(exam_history),
                    'average_score': round(avg_score, 2),
                    'highest_score': max(scores) if scores else 0,
                    'lowest_score': min(scores) if scores else 0
                },
                'exam_history': [
                    {
                        'exam_title': row.exam_title,
                        'score': row.score,
                        'submitted_at': row.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if row.submitted_at else None,
                        'duration_minutes': row.duration_minutes,
                        'total_questions': row.total_questions
                    }
                    for row in exam_history
                ],
                'wrong_questions': [
                    {
                        'question_text': row.question_text[:100] + '...' if len(row.question_text) > 100 else row.question_text,
                        'question_type': row.question_type,
                        'correct_answer': row.correct_answer,
                        'student_answer': row.student_answer,
                        'exam_title': row.exam_title
                    }
                    for row in wrong_questions
                ]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
