import { useState, useEffect, useRef } from 'react'

const API = '/api'

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('chatHistory')
    return saved ? JSON.parse(saved) : []
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState([])
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('sessionId'))
  const messagesEnd = useRef(null)

  useEffect(() => {
    if (token) fetchMe()
    fetchDocs()
  }, [token])

  useEffect(() => {
    if (user && !sessionId) {
      const newSession = user.user_id + '_' + Date.now()
      setSessionId(newSession)
      localStorage.setItem('sessionId', newSession)
    }
  }, [user, sessionId])

  // Persist messages to localStorage
  useEffect(() => {
    localStorage.setItem('chatHistory', JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchMe = async () => {
    try {
      const res = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) setUser(await res.json())
      else logout()
    } catch { logout() }
  }

  const fetchDocs = async () => {
    try {
      const res = await fetch(`${API}/documents`)
      if (res.ok) setDocs((await res.json()).documents || [])
    } catch {}
  }

  const login = async (username) => {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    if (res.ok) {
      const data = await res.json()
      localStorage.setItem('token', data.token)
      setToken(data.token)
      setUser(data.user)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('sessionId')
    localStorage.removeItem('chatHistory')
    setToken(null)
    setUser(null)
    setSessionId(null)
    setMessages([])
  }

  const newChat = () => {
    const newSession = user.user_id + '_' + Date.now()
    setSessionId(newSession)
    localStorage.setItem('sessionId', newSession)
    setMessages([])
    localStorage.removeItem('chatHistory')
  }

  const sendQuery = async () => {
    if (!input.trim()) return
    const q = input
    setInput('')
    setMessages(m => [...m, { role: 'user', content: q }])
    setLoading(true)

    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` })
        },
        body: JSON.stringify({ question: q, session_id: sessionId })
      })
      const data = await res.json()
      setMessages(m => [...m, { 
        role: 'assistant', 
        content: data.answer || data.detail,
        sources: data.sources,
        fromCache: data.from_cache,
        processingTime: data.processing_time_ms
      }])
    } catch (e) {
      setMessages(m => [...m, { role: 'assistant', content: 'Error: ' + e.message }])
    }
    setLoading(false)
  }

  const uploadFile = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    
    try {
      const res = await fetch(`${API}/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form
      })
      if (res.ok) {
        fetchDocs()
        alert('Uploaded: ' + file.name)
      }
    } catch (e) {
      alert('Upload failed: ' + e.message)
    }
    e.target.value = ''
  }

  const deleteDoc = async (source) => {
    if (!confirm(`Delete "${source}"?`)) return
    try {
      const res = await fetch(`${API}/documents/${encodeURIComponent(source)}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      if (res.ok) fetchDocs()
    } catch (e) {
      alert('Delete failed: ' + e.message)
    }
  }

  if (!user) {
    return (
      <div className="login-form">
        <h2>RAG v1 Login</h2>
        <select id="user-select" defaultValue="">
          <option value="" disabled>Select user...</option>
          <option value="admin">Admin</option>
          <option value="engineer">Engineer</option>
          <option value="hr_user">HR User</option>
          <option value="guest">Guest</option>
        </select>
        <button onClick={() => login(document.getElementById('user-select').value)}>
          Login
        </button>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="header">
        <h1>🤖 RAG v1 - Enterprise Knowledge Assistant</h1>
        <div className="user-info">
          {user.email} ({user.groups.join(', ')})
          <button onClick={logout} style={{marginLeft: 10, padding: '4px 8px', fontSize: '0.8rem'}}>Logout</button>
          <button onClick={newChat} style={{marginLeft: 5, padding: '4px 8px', fontSize: '0.8rem'}}>New Chat</button>
        </div>
      </div>

      <div className="main">
        <div className="sidebar">
          <div className="upload-section">
            <h3>📄 Upload Document</h3>
            <input type="file" onChange={uploadFile} accept=".txt,.pdf,.docx,.md" />
          </div>
          
          <div className="docs-list">
            <h3>📚 Documents ({docs.length})</h3>
            {docs.map((d, i) => (
              <div key={i} className="doc-item">
                <div className="doc-info">
                  <div>{d.source} ({d.chunks} chunks)</div>
                  {d.uploaded_at && <div className="doc-time">{new Date(d.uploaded_at).toLocaleString()}</div>}
                </div>
                <button className="delete-btn" onClick={() => deleteDoc(d.source)}>✕</button>
              </div>
            ))}
          </div>
        </div>

        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && (
              <div className="loading">Ask a question about your documents...</div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                {m.content}
                {m.fromCache && <span className="cache-badge">cached</span>}
                {m.processingTime && <span className="time-badge">{m.processingTime}ms</span>}
                {m.sources && m.sources.length > 0 && (
                  <div className="sources">
                    {m.sources.map((s, j) => (
                      <span key={j} className="source-item">
                        {s.source} <span className="relevance">({s.relevance}%)</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="loading">Thinking...</div>}
            <div ref={messagesEnd} />
          </div>
          
          <div className="input-area">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendQuery()}
              placeholder="Ask a question..."
              disabled={loading}
            />
            <button onClick={sendQuery} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
