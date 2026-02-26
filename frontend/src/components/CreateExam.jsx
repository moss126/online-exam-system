// frontend/src/components/CreateExam.jsx
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { API_BASE, authFetch } from '@/lib/apiBase'

/**
 * 修复点：
 * 1) 恢复右侧“题库选择”面板（手动选题模式可勾选题目）。
 * 2) 随机抽题支持“按分类数量”配置（为每个题型、每个分类设置数量）。
 * 3) 提交时根据 mode（manual/random）分别走 question_ids / random_config。
 * 4) 使用 authFetch 携带教师登录态，后端可写入 creator_id。
 */
export default function CreateExam() {
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const editExamId = sp.get('id') // 有 id 为编辑模式（仅替换题目 & 批量分值）

  const [mode, setMode] = useState('manual') // manual | random

  const [form, setForm] = useState({
    title: '',
    durationMinutes: 60,
    isRandomized: true,
    switchLimit: 3,
    defaultScore: 5,
    random_config: {
      single: { total: 0, byCategory: {} },
      multiple: { total: 0, byCategory: {} },
      true_false: { total: 0, byCategory: {} },
    },
    question_ids: []
  })

  const [bank, setBank] = useState([])
  const [categories, setCategories] = useState([])
  const [qTypeFilter, setQTypeFilter] = useState('')
  const [catFilter, setCatFilter] = useState('')
  const [search, setSearch] = useState('')
  const [msg, setMsg] = useState('')

  // 载入题库与分类
  const loadBank = async () => {
    try {
      const [qs, cs] = await Promise.all([
        fetch(`${API_BASE}/questions`).then(r=>r.json()),
        fetch(`${API_BASE}/categories`).then(r=>r.json()),
      ])
      if (qs.success) setBank(qs.questions || [])
      if (cs.success) setCategories(cs.categories || [])
    } catch {
      // 忽略
    }
  }
  useEffect(() => { loadBank() }, [])

  // 题库过滤
  const filtered = useMemo(() => {
    return bank.filter(q => {
      const byType = qTypeFilter ? q.question_type === qTypeFilter : true
      const byText = search ? (q.question_text || '').toLowerCase().includes(search.toLowerCase()) : true
      const byCat = catFilter ? String(q.category_id||'') === String(catFilter) : true
      return byType && byText && byCat
    })
  }, [bank, qTypeFilter, search, catFilter])

  // 勾选题目
  const togglePick = (id) => {
    const set = new Set(form.question_ids)
    if (set.has(id)) set.delete(id); else set.add(id)
    setForm({...form, question_ids: [...set]})
  }

  // 提交
  const submit = async (e) => {
    e.preventDefault()
    setMsg('')
    const payload = { ...form }
    if (mode === 'manual') delete payload.random_config
    else delete payload.question_ids

    try {
      let res, data
      if (editExamId) {
        // 编辑：整体替换（并支持批量默认分值）
        const updates = { replace: form.question_ids }
        res = await authFetch(`${API_BASE}/exam/${editExamId}/questions`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ updates, defaultScore: form.defaultScore })
        })
        data = await res.json()
      } else {
        res = await authFetch(`${API_BASE}/exams`, {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify(payload)
        })
        data = await res.json()
      }
      if (data.success) {
        setMsg(editExamId ? '试卷已更新' : '考试创建成功，正在返回列表...')
        setTimeout(()=>nav('/teacher/dashboard'), 800)
      } else {
        setMsg(data.message || '操作失败')
      }
    } catch {
      setMsg('网络错误，操作失败')
    }
  }

  return (
    <div>
      <h1 className="h1">{editExamId ? '编辑试卷（题目与分值）' : '创建新考试'}</h1>

      <form className="grid" style={{gridTemplateColumns:'repeat(12,1fr)', gap:16}} onSubmit={submit}>
        {/* 左：基础信息 & 抽题配置 */}
        <div className="card fancy" style={{gridColumn:'span 6'}}>
          <h3 className="h2">基础信息</h3>

          {!editExamId && (
            <>
              <label className="label mt16">考试名称</label>
              <input className="input" value={form.title}
                     onChange={e=>setForm({...form, title:e.target.value})} required />

              <label className="label mt16">考试时长（分钟）</label>
              <input className="input" type="number" min="1" value={form.durationMinutes}
                     onChange={e=>setForm({...form, durationMinutes:parseInt(e.target.value)||0})} required />

              <label className="label mt16">允许切屏次数（0 不限制）</label>
              <input className="input" type="number" min="0" value={form.switchLimit}
                     onChange={e=>setForm({...form, switchLimit:parseInt(e.target.value)||0})} />

              <div className="mt16">
                <label>
                  <input type="checkbox" checked={form.isRandomized}
                         onChange={e=>setForm({...form, isRandomized:e.target.checked})} /> 题目与选项乱序
                </label>
              </div>

              <div className="mt16">
                <label className="label">组卷方式</label>
                <div className="row">
                  <button type="button" className={`btn ${mode==='manual'?'':'outline'}`} onClick={()=>setMode('manual')}>手动选题</button>
                  <button type="button" className={`btn ${mode==='random'?'':'outline'}`} onClick={()=>setMode('random')}>随机抽题</button>
                </div>
              </div>
            </>
          )}

          <label className="label mt16">默认分值（支持批量设置）</label>
          <input className="input" type="number" min="1" value={form.defaultScore}
                 onChange={e=>setForm({...form, defaultScore:parseInt(e.target.value)||1})} />

          {/* 随机抽题：按分类配置 */}
          {mode === 'random' && !editExamId && (
            <div className="mt16">
              <div className="muted">为每个题型设置“总数”，也可为该题型下各分类设置数量（优先按分类，剩余再随机补足）。</div>
              {['single','multiple','true_false'].map(t=>{
                const title = t==='single'?'单选题':t==='multiple'?'多选题':'判断题'
                return (
                  <div className="card subtle mt16" key={t}>
                    <div className="h2">{title} 抽题设置</div>

                    <label className="label mt8">总数</label>
                    <input className="input" type="number" min="0"
                           value={form.random_config[t].total}
                           onChange={e=>{
                             const v = parseInt(e.target.value)||0
                             setForm({...form, random_config:{
                               ...form.random_config,
                               [t]: {...form.random_config[t], total: v}
                             }})
                           }} />

                    <div className="mt8">
                      <div className="muted" style={{marginBottom:8}}>按分类数量：</div>
                      <div className="row" style={{gap:8, flexWrap:'wrap'}}>
                        {categories.map(c=>(
                          <div key={c.id} className="badge" style={{padding:8}}>
                            <div style={{fontSize:12, marginBottom:6}}>{c.name}</div>
                            <input
                              className="input"
                              style={{maxWidth:80}}
                              type="number"
                              min="0"
                              value={form.random_config[t].byCategory?.[c.name] || 0}
                              onChange={e=>{
                                const v = parseInt(e.target.value)||0
                                const byCat = {...(form.random_config[t].byCategory||{})}
                                if (v<=0) delete byCat[c.name]; else byCat[c.name] = v
                                setForm({...form, random_config:{
                                  ...form.random_config, [t]: {...form.random_config[t], byCategory: byCat}
                                }})
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {msg && <div className="mt16 tip">{msg}</div>}
          <button className="btn mt16" type="submit">{editExamId?'保存修改':'创建考试'}</button>
        </div>

        {/* 右：题库面板（手动选题时展示） */}
        <div className="card fancy" style={{gridColumn:'span 6'}}>
          <h3 className="h2">题库（增删改 + 分类过滤）</h3>

          <div className="row mt16" style={{flexWrap:'wrap', gap:12}}>
            <input className="input" placeholder="搜索题干..." value={search} onChange={e=>setSearch(e.target.value)} />
            <select value={qTypeFilter} onChange={e=>setQTypeFilter(e.target.value)} className="input" style={{maxWidth:180}}>
              <option value="">所有题型</option>
              <option value="single">单选题</option>
              <option value="multiple">多选题</option>
              <option value="true_false">判断题</option>
            </select>
            <select value={catFilter} onChange={e=>setCatFilter(e.target.value)} className="input" style={{maxWidth:220}}>
              <option value="">所有分类</option>
              {categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          {/* 仅在手动模式下可勾选；随机模式下仅浏览 */}
          <div className="mt16" style={{maxHeight: 480, overflow:'auto', border:'1px solid var(--border)', borderRadius:8, padding:8}}>
            {filtered.length===0 ? <div className="muted">暂无题目</div> : (
              <ul style={{listStyle:'none', padding:0, margin:0}}>
                {filtered.map(q=>(
                  <li key={q.id} className="mt8 row" style={{justifyContent:'space-between', borderBottom:'1px solid var(--border)', paddingBottom:8}}>
                    <label style={{display:'flex', gap:8, alignItems:'flex-start'}}>
                      {mode==='manual' ? (
                        <input type="checkbox" checked={form.question_ids.includes(q.id)} onChange={()=>togglePick(q.id)} />
                      ) : (
                        <input type="checkbox" disabled />
                      )}
                      <div>
                        <div>{q.question_text}</div>
                        <div className="muted mt8">{q.question_type} {q.category_name?` / ${q.category_name}`:''}</div>
                      </div>
                    </label>

                    {/* 简易“删改”入口（弹窗改/删除） */}
                    <div className="row" style={{gap:8}}>
                      <button type="button" className="btn small outline" onClick={async ()=>{
                        const nt = prompt('修改题干：', q.question_text)
                        if (nt && nt.trim()){
                          await fetch(`${API_BASE}/questions/${q.id}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question_text: nt.trim()})})
                          loadBank()
                        }
                      }}>改</button>
                      <button type="button" className="btn small outline" onClick={async ()=>{
                        if (!confirm('确认删除该题目？')) return
                        await fetch(`${API_BASE}/questions/${q.id}`, {method:'DELETE'})
                        loadBank()
                      }}>删</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="muted mt8">
            {mode==='manual' ? `已选 ${form.question_ids.length} 道` : '随机抽题模式下，不在此处勾选题目'}
          </div>
        </div>
      </form>
    </div>
  )
}
