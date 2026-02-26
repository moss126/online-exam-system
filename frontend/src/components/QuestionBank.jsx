// frontend/src/components/QuestionBank.jsx
import { useEffect, useMemo, useState } from 'react'
import { API_BASE } from '@/lib/apiBase'

const emptyForm = {
  id: null,
  question_text: '',
  question_type: 'single',
  category_id: '',
  options: { A: '', B: '', C: '', D: '' },
  correct_answer: []
}

export default function QuestionBank() {
  const [list, setList] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [catFilter, setCatFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [delOpen, setDelOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [msg, setMsg] = useState('')

  // 分类创建
  const [catModal, setCatModal] = useState(false)
  const [catName, setCatName] = useState('')
  const [catMsg, setCatMsg] = useState('')

  // Excel 导入
  const [excelFile, setExcelFile] = useState(null)
  const [impMsg, setImpMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [qs, cs] = await Promise.all([
        fetch(`${API_BASE}/questions`).then(r=>r.json()),
        fetch(`${API_BASE}/categories`).then(r=>r.json()),
      ])
      if (qs.success) setList(qs.questions || [])
      if (cs.success) setCategories(cs.categories || [])
    } finally { setLoading(false) }
  }

  useEffect(()=>{ load() }, [])

  const filtered = useMemo(()=>{
    return (list||[]).filter(it=>{
      const okText = q ? (it.question_text||'').toLowerCase().includes(q.toLowerCase()) : true
      const okType = typeFilter ? it.question_type===typeFilter : true
      const okCat = catFilter ? String(it.category_id||'')===String(catFilter) : true
      return okText && okType && okCat
    })
  }, [list, q, typeFilter, catFilter])

  const openCreate = () => {
    setForm(structuredClone(emptyForm))
    setModalOpen(true)
  }

  const openEdit = (row) => {
    setForm({
      id: row.id,
      question_text: row.question_text || '',
      question_type: row.question_type || 'single',
      category_id: row.category_id || '',
      options: normalizeOptions(row.options),
      correct_answer: normalizeCorrectAnswerForUI(row.question_type, row.correct_answer)
    })
    setModalOpen(true)
  }

  const openDelete = (row) => {
    setForm({ id: row.id })
    setDelOpen(true)
  }

  const normalizeOptions = (opts) => {
    const base = { A:'', B:'', C:'', D:'' }
    if (!opts) return base
    const out = { ...base, ...opts }
    return out
  }

  const normalizeCorrectAnswerForUI = (type, ca) => {
    if (type === 'true_false') {
      if (Array.isArray(ca) && ca.length===1 && typeof ca[0]==='boolean') return ca
      if (typeof ca === 'boolean') return [ca]
      if (typeof ca === 'string') {
        const s = ca.trim().toLowerCase()
        return [s==='true' || s==='t' || s==='1' || s==='是' || s==='对']
      }
      return [false]
    }
    if (type === 'multiple') {
      if (Array.isArray(ca)) return ca.map(x=>String(x).toUpperCase())
      if (typeof ca === 'string') return ca.split(/[,，]/).map(s=>s.trim().toUpperCase()).filter(Boolean)
      return []
    }
    if (Array.isArray(ca)) return ca.length? [String(ca[0]).toUpperCase()] : []
    if (typeof ca === 'string') return [ca.toUpperCase()]
    return []
  }

  const packCorrectAnswerForSave = (type) => {
    if (type === 'true_false') {
      const v = Array.isArray(form.correct_answer) ? form.correct_answer[0] : form.correct_answer
      return [!!v]
    }
    if (type === 'multiple') {
      const arr = Array.isArray(form.correct_answer) ? form.correct_answer : String(form.correct_answer||'').split(/[,，]/)
      return arr.map(s=>String(s).trim().toUpperCase()).filter(Boolean)
    }
    const v = Array.isArray(form.correct_answer) ? (form.correct_answer[0]||'') : String(form.correct_answer||'')
    return [v.toUpperCase()]
  }

  const cleanupOptions = (opts) => {
    if (!opts) return null
    const out = {}
    ;['A','B','C','D','E','F'].forEach(k=>{
      const v = (opts[k]??'').toString().trim()
      if (v) out[k]=v
    })
    return Object.keys(out).length? out : null
  }

  const save = async () => {
    setMsg('')
    const payload = {
      question_text: form.question_text.trim(),
      question_type: form.question_type,
      category_id: form.category_id || null,   // 单选分类
      options: cleanupOptions(form.options),
      correct_answer: packCorrectAnswerForSave(form.question_type)
    }
    if (!payload.question_text) { setMsg('题干不能为空'); return }
    if (form.question_type!=='true_false') {
      const hasAny = Object.values(payload.options||{}).some(v=>v && String(v).trim()!=='')
      if (!hasAny) { setMsg('请至少填写一个选项'); return }
    }

    if (form.id) {
      await fetch(`${API_BASE}/questions/${form.id}`, {
        method:'PUT',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      })
    } else {
      await fetch(`${API_BASE}/questions`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ ...payload, creator_id: 1 })
      })
    }
    setModalOpen(false)
    await load()
  }

  const doDelete = async () => {
    await fetch(`${API_BASE}/questions/${form.id}`, { method:'DELETE' })
    setDelOpen(false)
    await load()
  }

  // —— 分类：新建 —— //
  const openCreateCategory = () => { setCatName(''); setCatMsg(''); setCatModal(true) }
  const createCategory = async () => {
    setCatMsg('')
    const name = (catName||'').trim()
    if (!name) { setCatMsg('分类名不能为空'); return }
    const res = await fetch(`${API_BASE}/categories`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name })
    })
    const data = await res.json()
    if (!data.success) { setCatMsg(data.message || '创建失败'); return }
    setCatModal(false)
    await load()
  }

  // —— Excel 导入 —— //
  const uploadExcel = async () => {
    if (!excelFile) { setImpMsg('请先选择Excel文件'); return }
    setImpMsg('正在导入…')
    const fd = new FormData()
    fd.append('file', excelFile)
    try {
      const res = await fetch(`${API_BASE}/questions/upload`, { method:'POST', body: fd })
      const data = await res.json()
      setImpMsg(data.message || (data.success?'导入成功':'导入失败'))
      if (data.success) { setExcelFile(null); await load() }
    } catch {
      setImpMsg('导入失败（网络错误）')
    }
  }
  const downloadTemplate = () => {
    window.open(`${API_BASE}/questions/template`, '_blank')
  }

  return (
    <div>
      <div className="row" style={{justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
        <h1 className="h1">题库管理</h1>
        <div className="row">
          <button className="btn outline" onClick={openCreateCategory}>新建分类</button>
          <button className="btn" onClick={openCreate}>新建题目</button>
        </div>
      </div>

      <div className="card fancy">
        <div className="row" style={{flexWrap:'wrap', gap:12}}>
          <input className="input" placeholder="搜索题干…" value={q} onChange={e=>setQ(e.target.value)} />
          <select className="input" style={{maxWidth:160}} value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}>
            <option value="">所有题型</option>
            <option value="single">单选题</option>
            <option value="multiple">多选题</option>
            <option value="true_false">判断题</option>
          </select>
          <select className="input" style={{maxWidth:200}} value={catFilter} onChange={e=>setCatFilter(e.target.value)}>
            <option value="">所有分类</option>
            {categories.map(c=> <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        {/* Excel 导入区域 */}
        <div className="mt16 card subtle">
          <div className="h2">Excel 导入题库</div>
          <div className="row mt8" style={{flexWrap:'wrap', gap:12}}>
            <input type="file" accept=".xls,.xlsx" onChange={e=>setExcelFile(e.target.files?.[0]||null)} />
            <button className="btn outline" onClick={uploadExcel}>上传导入</button>
            <button className="btn outline" onClick={downloadTemplate}>下载中文模板</button>
            {impMsg && <span className="muted">{impMsg}</span>}
          </div>
          <div className="mt8 muted" style={{fontSize:13}}>
            模板列：题干、题型（单选题/多选题/判断题）、分类、选项A~选项D、正确答案。<br/>
            示例：单选题填 <code>A</code>；多选题填 <code>A,C</code>；判断题填 <code>对/错</code> 或 <code>True/False</code>。
          </div>
        </div>

        <div className="mt16" style={{maxHeight: 540, overflow:'auto'}}>
          {loading ? <div className="center">加载中...</div> : (
            filtered.length===0 ? <div className="muted">暂无题目</div> : (
              <table className="table">
                <thead>
                  <tr><th style={{width:'50%'}}>题干</th><th>题型</th><th>分类</th><th>操作</th></tr>
                </thead>
                <tbody>
                  {filtered.map(row=>(
                    <tr key={row.id}>
                      <td>{row.question_text}</td>
                      <td>{row.question_type}</td>
                      <td>{row.category_name || '-'}</td>
                      <td className="row" style={{gap:8}}>
                        <button className="btn small outline" onClick={()=>openEdit(row)}>编辑</button>
                        <button className="btn small outline" onClick={()=>openDelete(row)}>删除</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
        </div>
      </div>

      {/* 题目弹窗：新建/编辑 */}
      {modalOpen && (
        <div style={backdropStyle}>
          <div style={modalStyle} className="card">
            <div className="h2">{form.id ? '编辑题目' : '新建题目'}</div>
            <div className="mt12">
              <label className="label">题干</label>
              <textarea className="input" rows={3} value={form.question_text} onChange={e=>setForm({...form, question_text:e.target.value})} />
            </div>

            <div className="row mt12" style={{flexWrap:'wrap', gap:12}}>
              <div>
                <label className="label">题型</label>
                <select className="input" value={form.question_type} onChange={e=>{
                  const t = e.target.value
                  setForm({
                    ...form,
                    question_type: t,
                    correct_answer: t==='true_false' ? [false] : []
                  })
                }}>
                  <option value="single">单选题</option>
                  <option value="multiple">多选题</option>
                  <option value="true_false">判断题</option>
                </select>
              </div>

              <div>
                <label className="label">分类（单选）</label>
                <select className="input" value={form.category_id ?? ''} onChange={e=>setForm({...form, category_id: e.target.value})}>
                  <option value="">无分类</option>
                  {categories.map(c=> <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>

            {form.question_type !== 'true_false' && (
              <div className="mt12">
                <div className="h2">选项</div>
                {['A','B','C','D','E','F'].map(k=>(
                  <div key={k} className="row mt8">
                    <label className="label" style={{width:28}}>{k}</label>
                    <input
                      className="input"
                      value={form.options?.[k] || ''}
                      onChange={e=>setForm({...form, options:{...(form.options||{}), [k]: e.target.value}})}
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="mt12">
              <div className="h2">正确答案</div>
              {form.question_type==='true_false' && (
                <div className="row mt8">
                  <label className="row option">
                    <input type="radio" checked={!!form.correct_answer?.[0]===true} onChange={()=>setForm({...form, correct_answer:[true]})} /> 正确
                  </label>
                  <label className="row option">
                    <input type="radio" checked={!!form.correct_answer?.[0]===false} onChange={()=>setForm({...form, correct_answer:[false]})} /> 错误
                  </label>
                </div>
              )}
              {form.question_type==='single' && (
                <input
                  className="input"
                  placeholder="例如：A"
                  value={Array.isArray(form.correct_answer)?(form.correct_answer[0]||''):''}
                  onChange={e=>setForm({...form, correct_answer:[e.target.value.toUpperCase()]})}
                />
              )}
              {form.question_type==='multiple' && (
                <input
                  className="input"
                  placeholder="例如：A,C,D（用逗号分隔）"
                  value={Array.isArray(form.correct_answer)?form.correct_answer.join(','):''}
                  onChange={e=>{
                    const arr = e.target.value.split(/[,，]/).map(s=>s.trim().toUpperCase()).filter(Boolean)
                    setForm({...form, correct_answer: arr})
                  }}
                />
              )}
            </div>

            {msg && <div className="tip mt12">{msg}</div>}

            <div className="row mt16" style={{justifyContent:'flex-end'}}>
              <button className="btn outline" onClick={()=>setModalOpen(false)}>取消</button>
              <button className="btn" onClick={save}>保存</button>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认弹窗 */}
      {delOpen && (
        <div style={backdropStyle}>
          <div style={modalStyle} className="card">
            <div className="h2">确认删除该题目？</div>
            <div className="row mt16" style={{justifyContent:'flex-end'}}>
              <button className="btn outline" onClick={()=>setDelOpen(false)}>取消</button>
              <button className="btn" onClick={doDelete}>删除</button>
            </div>
          </div>
        </div>
      )}

      {/* 新建分类弹窗 */}
      {catModal && (
        <div style={backdropStyle}>
          <div style={modalStyle} className="card">
            <div className="h2">新建分类</div>
            <div className="mt12">
              <label className="label">分类名称</label>
              <input className="input" value={catName} onChange={e=>setCatName(e.target.value)} />
            </div>
            {catMsg && <div className="tip mt12">{catMsg}</div>}
            <div className="row mt16" style={{justifyContent:'flex-end'}}>
              <button className="btn outline" onClick={()=>setCatModal(false)}>取消</button>
              <button className="btn" onClick={createCategory}>创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const backdropStyle = {
  position:'fixed', inset:0, background:'rgba(0,0,0,.25)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:50
}
const modalStyle = { width:'min(720px, 96vw)' }
