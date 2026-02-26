// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import TeacherDashboard from '@/components/TeacherDashboard'
import CreateExam from '@/components/CreateExam'
import ExamTaking from '@/components/ExamTaking'
import StudentDashboard from '@/components/StudentDashboard'
import Analytics from '@/components/Analytics'
import QuestionBank from '@/components/QuestionBank'
import TeacherLogin from '@/components/TeacherLogin'
import StudentLogin from '@/components/StudentLogin'
import Header from '@/components/Header'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Header />
      <div className="container">
        <Routes>
          <Route path="/" element={<Navigate to="/student/login" replace />} />
          {/* 登录 */}
          <Route path="/teacher/login" element={<TeacherLogin />} />
          <Route path="/student/login" element={<StudentLogin />} />
          {/* 教师端 */}
          <Route path="/teacher/dashboard" element={<TeacherDashboard />} />
          <Route path="/teacher/create-exam" element={<CreateExam />} />
          <Route path="/teacher/questions" element={<QuestionBank />} />
          <Route path="/teacher/analytics" element={<Analytics />} />
          {/* 学生端 */}
          <Route path="/student/dashboard" element={<StudentDashboard />} />
          <Route path="/student/exam/:id" element={<ExamTaking />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
