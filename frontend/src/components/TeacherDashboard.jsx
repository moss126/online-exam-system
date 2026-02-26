// frontend/src/components/TeacherDashboard.jsx
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { API_BASE } from '@/lib/apiBase'

export default function TeacherDashboard() {
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)
  const nav = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/teacher/exams`)
      const data = await res.json()
      if (data.success) setExams(data.exams || [])
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const toggleExam = async (id) => {
    await fetch(`${API_BASE}/exam/${id}/toggle`, { method: 'POST', headers:{'Content-Type':'application/json'} })
    load()
  }

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
        <h1 className="h1">教师端 · 考试管理</h1>
        <div className="row">
          <Link className="btn outline" to="/teacher/analytics">数据分析</Link>
          <Link className="btn outline" to="/teacher/questions">题库管理</Link>
          <Link className="btn" to="/teacher/create-exam">创建考试</Link>
        </div>
      </div>

      <div className="card fancy">
        {loading ? (
          <div className="center">加载中...</div>
        ) : exams.length === 0 ? (
          <div className="muted">暂无考试</div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>名称</th><th>时长</th><th>状态</th><th>操作</th></tr>
            </thead>
            <tbody>
              {exams.map(e => (
                <tr key={e.id}>
                  <td>{e.title}</td>
                  <td>{e.duration_minutes} 分钟</td>
                  <td><span className={`badge ${e.is_open?'on':'off'}`}>{e.is_open ? '已发布' : '未发布'}</span></td>
                  <td className="row" style={{gap:8}}>
                    <button className="btn small" onClick={()=>toggleExam(e.id)}>{e.is_open?'取消发布':'发布'}</button>
                    <button className="btn small outline" onClick={()=>nav(`/teacher/create-exam?id=${e.id}`)}>编辑题目/分值</button>
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
