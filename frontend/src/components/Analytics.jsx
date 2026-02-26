// frontend/src/components/Analytics.jsx
import { useEffect, useState } from 'react'
import { API_BASE } from '@/lib/apiBase'
import './analytics.css'

export default function Analytics() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState({ total_exams:0, total_participants:0, avg_score:0, max_score:0, score_buckets:[], exams:[] })

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailExam, setDetailExam] = useState(null)
  const [subs, setSubs] = useState([])
  const [subsLoading, setSubsLoading] = useState(false)

  const [ansOpen, setAnsOpen] = useState(false)
  const [ansLoading, setAnsLoading] = useState(false)
  const [ansMeta, setAnsMeta] = useState(null)
  const [answers, setAnswers] = useState([])

  useEffect(()=>{
    (async ()=>{
      setLoading(true)
      const res = await fetch(`${API_BASE}/analytics/teacher/overview`)
      const d = await res.json()
      if (d.success) setData(d.data || d)
      setLoading(false)
    })()
  }, [])

  const openDetail = async (exam) => {
    setDetailExam(exam)
    setDetailOpen(true)
    setSubs([])
    setSubsLoading(true)
    const res = await fetch(`${API_BASE}/analytics/exam/${exam.id}/submissions`)
    const d = await res.json()
    if (d.success) setSubs(d.submissions || [])
    setSubsLoading(false)
  }

  const openAnswers = async (attemptId) => {
    setAnsOpen(true)
    setAnsLoading(true)
    setAnswers([])
    setAnsMeta(null)
    const res = await fetch(`${API_BASE}/analytics/attempt/${attemptId}/answers`)
    const d = await res.json()
    if (d.success) {
      setAnsMeta(d.attempt)
      setAnswers(d.answers || [])
    }
    setAnsLoading(false)
  }

  if (loading) return <div className="center">加载分析数据...</div>

  const cards = [
    { label:'考试总数', value: data.total_exams },
    { label:'参与人数', value: data.total_participants },
    { label:'平均分', value: (data.avg_score ?? 0).toFixed(1) },
    { label:'最高分', value: data.max_score || 0 },
  ]

  return (
    <div>
      <h1 className="h1">数据分析</h1>

      <div className="ana-grid">
        {cards.map((c,i)=>(
          <div key={i} className="ana-card">
            <div className="ana-value">{c.value}</div>
            <div className="ana-label">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="ana-panel">
        <div className="ana-title">近期考试成绩分布</div>
        <div className="ana-bars">
          {(data.score_buckets || []).map((b, i)=>(
            <div key={i} className="ana-bar">
              <div className="ana-bar-inner" style={{height: Math.min(120, (b.count||0) * 10) + 'px'}} />
              <div className="ana-bar-label">{b.range}</div>
              <div className="ana-bar-count">{b.count}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="ana-panel" style={{marginTop:16}}>
        <div className="ana-title">考试列表</div>
        {data.exams?.length ? (
          <table className="table">
            <thead>
              <tr><th>名称</th><th>提交数</th><th>均分</th><th>最高分</th><th>操作</th></tr>
            </thead>
            <tbody>
              {data.exams.map(e=>(
                <tr key={e.id}>
                  <td>{e.title}</td>
                  <td>{e.attempts}</td>
                  <td>{(e.avg_score ?? 0).toFixed(1)}</td>
                  <td>{e.max_score || 0}</td>
                  <td><button className="btn small" onClick={()=>openDetail(e)}>查看提交</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <div className="muted">暂无考试数据</div>}
      </div>

      {/* 提交明细弹窗 */}
      {detailOpen && (
        <div style={backdropStyle}>
          <div style={modalStyle} className="card">
            <div className="h2">提交明细 · {detailExam?.title}</div>
            {subsLoading ? <div className="center">加载中...</div> : (
              subs.length === 0 ? <div className="muted mt8">暂无提交</div> : (
                <div className="mt12" style={{maxHeight:480, overflow:'auto'}}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th style={{width:140}}>学生姓名</th>
                        <th style={{width:120}}>工号</th>
                        <th style={{width:100}}>得分</th>
                        <th style={{width:160}}>提交时间</th>
                        <th style={{width:100}}>切屏次数</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subs.map(s=>(
                        <tr key={s.attempt_id}>
                          <td>{s.student_name || '-'}</td>
                          <td>{s.employee_no || s.student_id || '-'}</td>
                          <td>{s.final_score}</td>
                          <td>{s.submit_time || '-'}</td>
                          <td>{s.switch_count}</td>
                          <td>
                            <button className="btn small" onClick={()=>openAnswers(s.attempt_id)}>答题明细</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
            <div className="row mt12" style={{justifyContent:'flex-end'}}>
              <button className="btn outline" onClick={()=>setDetailOpen(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* 单份提交：答题明细弹窗 */}
      {ansOpen && (
        <div style={backdropStyle}>
          <div style={{...modalStyle, width:'min(1040px, 96vw)'}} className="card">
            <div className="h2">答题明细 {ansMeta ? `· ${ansMeta.student_name || '-'}（工号：${ansMeta.employee_no || ansMeta.student_id || '-' }）` : ''}</div>
            {ansLoading ? <div className="center">加载中...</div> : (
              answers.length===0 ? <div className="muted mt8">无答题记录</div> : (
                <div className="mt12" style={{maxHeight:520, overflow:'auto'}}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th style={{width:60}}>#</th>
                        <th>题干</th>
                        <th style={{width:160}}>正确答案</th>
                        <th style={{width:160}}>作答</th>
                        <th style={{width:80}}>判定</th>
                      </tr>
                    </thead>
                    <tbody>
                      {answers.map((a, idx)=>(
                        <tr key={idx}>
                          <td>{idx+1}</td>
                          <td>{a.question_text}</td>
                          <td>{Array.isArray(a.correct_answer)?a.correct_answer.join(','):String(a.correct_answer)}</td>
                          <td>{Array.isArray(a.student_answer)?a.student_answer.join(','):String(a.student_answer)}</td>
                          <td>{a.is_correct ? '✅' : '❌'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
            <div className="row mt12" style={{justifyContent:'flex-end'}}>
              <button className="btn outline" onClick={()=>setAnsOpen(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const backdropStyle = { position:'fixed', inset:0, background:'rgba(0,0,0,.25)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:50 }
const modalStyle = { width:'min(960px, 96vw)' }
