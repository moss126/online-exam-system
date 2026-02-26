// frontend/src/components/TeacherLogin.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '@/lib/apiBase'

export default function TeacherLogin() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      const res = await fetch(`${API_BASE}/auth/teacher/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      const data = await res.json()
      if (!data.success) { setMsg(data.message || '登录失败'); return }
      localStorage.setItem('token', data.token)
      localStorage.setItem('role', 'teacher')
      localStorage.setItem('user', JSON.stringify(data.user))
      nav('/teacher/dashboard')
    } catch {
      setMsg('网络错误')
    }
  }

  return (
    <div className="center">
      <form className="card fancy" style={{width:360}} onSubmit={submit}>
        <h1 className="h1">教师登录</h1>
        <label className="label mt8">账号</label>
        <input className="input" value={username} onChange={e=>setUsername(e.target.value)} />
        <label className="label mt8">密码</label>
        <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
        {msg && <div className="tip mt8">{msg}</div>}
        <button className="btn mt12" type="submit">登录</button>
      </form>
    </div>
  )
}
