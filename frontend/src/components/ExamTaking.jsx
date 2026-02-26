// frontend/src/components/ExamTaking.jsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE, authFetch } from '@/lib/apiBase'

/**
 * 修复点（多选题显示错乱/受控警告）：
 * 1) 统一归一化题目 options，兼容 Object / Array / JSON-string，自动补 A/B/C/D 序号。
 * 2) 加载题目后为不同题型初始化 answers（single:''，multiple:[]，true_false:null），
 *    彻底消除 controlled ↔ uncontrolled 警告。
 * 3) 多选题用数组保存所选项；渲染时严格以归一化后的 key 显示（A/B/C...）。
 */
export default function ExamTaking() {
  const { id } = useParams()
  const nav = useNavigate()

  const [exam, setExam] = useState(null)
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({}) // { [qid]: '', [] or true/false }
  const [left, setLeft] = useState(60 * 60) // 秒
  const [switchCount, setSwitchCount] = useState(0)
  const timerRef = useRef(null)

  // 学生登录信息
  const user = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} }
  }, [])
  const role = localStorage.getItem('role') || ''

  // 未登录学生则跳转
  useEffect(() => {
    if (role !== 'student' || !user?.name) {
      alert('请先使用学生账号登录')
      nav('/student/login', { replace: true })
    }
  }, [role, user?.name, nav])

  // 归一化 options：返回 [{key:'A', text:'xxx'}, ...]
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')
  const normalizeOptions = (raw) => {
    if (!raw) return []
    let obj = raw
    if (typeof raw === 'string') {
      try { obj = JSON.parse(raw) } catch { /* 兜底 */ }
    }
    // Object -> entries；Array -> 索引赋 A/B/C
    if (Array.isArray(obj)) {
      return obj.map((txt, i) => ({ key: letters[i] || String(i+1), text: String(txt) }))
    }
    if (typeof obj === 'object') {
      return Object.entries(obj).map(([k, v]) => ({ key: String(k), text: String(v) }))
    }
    // 单值兜底
    return [{ key: 'A', text: String(obj) }]
  }

  // 加载试卷
  useEffect(() => {
    (async () => {
      const res = await authFetch(`${API_BASE}/exam/${id}`)
      const data = await res.json()
      if (!data.success) { alert(data.message || '试卷不存在'); nav('/student/dashboard'); return }
      const qs = (data.questions || []).map(q => ({
        ...q,
        _opts: normalizeOptions(q.options)
      }))
      setExam(data.exam)
      setQuestions(qs)
      setLeft((data.exam?.duration_minutes || 60) * 60)

      // 初始化 answers，避免受控警告 & 多选题默认 []
      const init = {}
      qs.forEach(q => {
        if (q.question_type === 'multiple') init[q.id] = []
        else if (q.question_type === 'true_false') init[q.id] = null
        else init[q.id] = '' // single
      })
      setAnswers(init)
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  // 计时
  useEffect(() => {
    timerRef.current && clearInterval(timerRef.current)
    timerRef.current = setInterval(() => setLeft(s => (s > 0 ? s - 1 : 0)), 1000)
    return () => timerRef.current && clearInterval(timerRef.current)
  }, [])

  // 切屏计数
  useEffect(() => {
    const onVis = () => { if (document.hidden) setSwitchCount(c => c + 1) }
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  const setAns = (qid, v) => setAnswers(a => ({ ...a, [qid]: v }))

  const submit = async () => {
    const payload = {
      answers: Object.entries(answers).map(([qid, v]) => ({ question_id: Number(qid), answer: v })),
      switch_count: switchCount,
      student_name: user?.name || '',
      employee_no: user?.id || user?.employee_no || ''
    }
    try {
      const res = await authFetch(`${API_BASE}/exam/${id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!data.success) { alert(data.message || '提交失败'); return }
      alert(`提交成功，得分：${data.score}`)
      nav('/student/dashboard')
    } catch {
      alert('网络错误，提交失败')
    }
  }

  if (!exam) return <div className="center">加载中…</div>

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between', alignItems:'center', marginBottom:12}}>
        <h1 className="h1">{exam.title}</h1>
        <div className="row" style={{gap:12}}>
          <span className="muted">【{user?.name || '未登录'}】</span>
          <span>剩余时间：{Math.floor(left/60)}:{String(left%60).padStart(2,'0')}　切屏：{switchCount} 次</span>
          <button className="btn" onClick={submit}>提交试卷</button>
        </div>
      </div>

      {/* 题型分组 + 题型说明 */}
      {['single','multiple','true_false'].map(type=>{
        const group = questions.filter(q=>q.question_type===type)
        if (group.length===0) return null
        const title = type==='single'?'单选题（每题仅选择一个正确答案）'
                    : type==='multiple'?'多选题（可能有多个正确答案）'
                    : '判断题（对/错）'
        return (
          <div key={type} className="card fancy mt16">
            <div className="h2">{title}</div>
            {group.map((q, idx)=>(
              <div key={q.id} className="mt12" style={{borderTop:'1px dashed var(--border)', paddingTop:12}}>
                <div className="h3">{idx+1}、{q.question_text}</div>

                {type==='true_false' ? (
                  <div className="row mt8">
                    <label className="row option">
                      <input type="radio" name={`q_${q.id}`} checked={answers[q.id]===true} onChange={()=>setAns(q.id, true)} /> 正确
                    </label>
                    <label className="row option">
                      <input type="radio" name={`q_${q.id}`} checked={answers[q.id]===false} onChange={()=>setAns(q.id, false)} /> 错误
                    </label>
                  </div>
                ) : type==='single' ? (
                  <div className="col mt8">
                    {q._opts.map(opt=>(
                      <label className="row option" key={opt.key}>
                        <input
                          type="radio"
                          name={`q_${q.id}`}
                          checked={answers[q.id]===opt.key}
                          onChange={()=>setAns(q.id, opt.key)}
                        />
                        <span>{opt.key}. {opt.text}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <div className="col mt8">
                    {q._opts.map(opt=>(
                      <label className="row option" key={opt.key}>
                        <input
                          type="checkbox"
                          checked={Array.isArray(answers[q.id]) ? answers[q.id].includes(opt.key) : false}
                          onChange={e=>{
                            const cur = Array.isArray(answers[q.id]) ? [...answers[q.id]] : []
                            if (e.target.checked) {
                              if (!cur.includes(opt.key)) cur.push(opt.key)
                            } else {
                              const i = cur.indexOf(opt.key); if (i>-1) cur.splice(i,1)
                            }
                            setAns(q.id, cur)
                          }}
                        />
                        <span>{opt.key}. {opt.text}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
