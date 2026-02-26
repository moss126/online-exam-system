// frontend/src/components/Header.jsx
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

export default function Header() {
  const nav = useNavigate()
  const loc = useLocation()
  const [role, setRole] = useState(localStorage.getItem('role') || '')
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} }
  })

  // 当路由或本地存储变化时刷新头部
  useEffect(() => {
    const sync = () => {
      setRole(localStorage.getItem('role') || '')
      try { setUser(JSON.parse(localStorage.getItem('user') || '{}')) } catch { setUser({}) }
    }
    sync()
    const onStorage = () => sync()
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [loc.pathname])

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('user')
    // 分角色回到对应登录页
    nav(role === 'teacher' ? '/teacher/login' : '/student/login', { replace: true })
  }

  return (
    <div className="nav">
      <div className="nav-inner">
        <strong>在线考试系统</strong>
        <div className="row" style={{gap:12}}>
          {/* 教师端导航 */}
          {role === 'teacher' && (
            <>
              <Link to="/teacher/create-exam">创建考试</Link>
              <Link to="/teacher/questions">题库管理</Link>
              <Link to="/teacher/analytics">数据分析</Link>
            </>
          )}

          {/* 右侧：账号与退出（学生与教师都显示） */}
          {role ? (
            <>
              <span className="muted">【{user?.name || (role==='teacher'?'教师':'学生')}】</span>
              <button className="btn small outline" onClick={logout}>退出</button>
            </>
          ) : (
            // 未登录：提供入口
            <>
              <Link to="/teacher/login">教师登录</Link>
              <Link to="/student/login">学生登录</Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
