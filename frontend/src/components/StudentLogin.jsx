// frontend/src/components/StudentLogin.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE } from '@/lib/apiBase'

export default function StudentLogin() {
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [employeeNo, setEmployeeNo] = useState('')
  const [msg, setMsg] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    try {
      const res = await fetch(`${API_BASE}/auth/student/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, employee_no: employeeNo })
      })
      const data = await res.json()
      if (!data.success) { setMsg(data.message || '登录失败'); return }
      localStorage.setItem('token', data.token)
      localStorage.setItem('role', 'student')
      localStorage.setItem('user', JSON.stringify(data.user))
      nav('/student/dashboard')
    } catch {
      setMsg('网络错误')
    }
  }

  return (
    <div className="center">
      <form className="card fancy" style={{width:360}} onSubmit={submit}>
        <h1 className="h1">学生登录</h1>
        <label className="label mt8">姓名</label>
        <input className="input" value={name} onChange={e=>setName(e.target.value)} />
        <label className="label mt8">工号</label>
        <input className="input" value={employeeNo} onChange={e=>setEmployeeNo(e.target.value)} />
        {msg && <div className="tip mt8">{msg}</div>}
        <button className="btn mt12" type="submit">进入</button>
      </form>
    </div>
  )
}
