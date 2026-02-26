// frontend/src/components/StudentDashboard.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '@/lib/apiBase'

export default function StudentDashboard() {
  const nav = useNavigate()
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/student/exams`)
      const data = await res.json()
      if (data.success) setExams(data.exams || [])
    } finally { setLoading(false) }
  }

  useEffect(()=>{ load() }, [])

  return (
    <div>
      <h1 className="h1">学生端 · 可参加考试</h1>
      <div className="card fancy">
        {loading ? (
          <div className="center">加载中...</div>
        ) : exams.length === 0 ? (
          <div className="muted">当前没有已发布的考试</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>名称</th><th>时长</th><th>操作</th></tr>
            </thead>
            <tbody>
              {exams.map(e=>(
                <tr key={e.id}>
                  <td>{e.title}</td>
                  <td>{e.duration_minutes} 分钟</td>
                  <td>
                    <button className="btn small" onClick={()=>nav(`/student/exam/${e.id}`)}>进入考试</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
