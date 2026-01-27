import { useState, useEffect, useRef } from 'react'

// API endpoint - empty string when on CloudFront (uses cache behaviors to route to ALB)
// For local dev, set VITE_API_URL env var or it defaults to localhost
const API = window.location.hostname.includes('cloudfront.net') 
  ? '' 
  : (import.meta.env.VITE_API_URL || '')

// Format message with markdown-like rendering
const formatMessage = (text) => {
  if (!text) return ''
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/^\s*(\d+)\.\s+(.+)$/gm, '<li>$2</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
}

function App() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [selectedUser, setSelectedUser] = useState('')
  const [allChats, setAllChats] = useState(() => {
    const saved = localStorage.getItem('allChats')
    return saved ? JSON.parse(saved) : {}
  })
  const [currentChatId, setCurrentChatId] = useState(() => localStorage.getItem('currentChatId'))
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [docs, setDocs] = useState([])
  const messagesEnd = useRef(null)

  // Load messages for current chat
  useEffect(() => {
    if (currentChatId && allChats[currentChatId]) {
      setMessages(allChats[currentChatId].messages || [])
    } else {
      setMessages([])
    }
  }, [currentChatId, allChats])

  useEffect(() => {
    if (token) fetchMe()
    fetchDocs()
  }, [token])

  // Save messages to allChats
  useEffect(() => {
    if (currentChatId && messages.length > 0) {
      setAllChats(prev => {
        const updated = {
          ...prev,
          [currentChatId]: { messages, timestamp: Date.now() }
        }
        localStorage.setItem('allChats', JSON.stringify(updated))
        return updated
      })
    }
  }, [messages, currentChatId])

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
      // Create new chat if none exists
      if (!currentChatId) {
        const newId = data.user.user_id + '_' + Date.now()
        setCurrentChatId(newId)
        localStorage.setItem('currentChatId', newId)
      }
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    // Keep allChats and currentChatId for when user logs back in
  }

  const newChat = () => {
    const newId = user.user_id + '_' + Date.now()
    setCurrentChatId(newId)
    localStorage.setItem('currentChatId', newId)
    setMessages([])
  }

  const switchChat = (chatId) => {
    setCurrentChatId(chatId)
    localStorage.setItem('currentChatId', chatId)
  }

  const deleteChat = (chatId) => {
    setAllChats(prev => {
      const updated = { ...prev }
      delete updated[chatId]
      localStorage.setItem('allChats', JSON.stringify(updated))
      return updated
    })
    if (chatId === currentChatId) {
      newChat()
    }
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
        body: JSON.stringify({ question: q, session_id: currentChatId })
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
        <h2>☁️ RAG Cloud Login</h2>
        <select id="user-select">
          <option value="admin">Admin</option>
          <option value="engineer">Engineer</option>
          <option value="guest">Guest</option>
        </select>
        <button onClick={() => login(document.getElementById('user-select').value)}>Login</button>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="header">
        <h1>☁️ RAG Cloud - Knowledge Assistant</h1>
        <div className="user-info">
          {user.email}
          <button onClick={logout}>Logout</button>
          <button onClick={newChat}>New Chat</button>
        </div>
      </div>

      <div className="main">
        <div className="sidebar">
          <div className="upload-section">
            <h3>📄 Upload</h3>
            <input type="file" onChange={uploadFile} accept=".txt,.pdf,.md" />
          </div>
          <div className="docs-list">
            <h3>📚 Documents ({docs.length})</h3>
            {docs.map((d, i) => (
              <div key={i} className="doc-item">
                <span>{d.source} ({d.chunks})</span>
                <button className="delete-btn" onClick={() => deleteDoc(d.source)}>✕</button>
              </div>
            ))}
          </div>
          <div className="chats-list">
            <h3>💬 Chat History</h3>
            {Object.entries(allChats)
              .sort((a, b) => b[1].timestamp - a[1].timestamp)
              .map(([id, chat]) => (
                <div key={id} className={`chat-item ${id === currentChatId ? 'active' : ''}`} onClick={() => switchChat(id)}>
                  <span>{chat.messages?.[0]?.content?.slice(0, 30) || 'New chat'}...</span>
                  <button className="delete-btn" onClick={(e) => { e.stopPropagation(); deleteChat(id); }}>✕</button>
                </div>
              ))}
          </div>
        </div>

        <div className="chat">
          <div className="messages">
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                <div className="content" dangerouslySetInnerHTML={{ __html: formatMessage(m.content) }} />
                {m.sources?.length > 0 && (
                  <div className="sources">
                    Sources: {[...new Set(m.sources.map(s => s.source))].join(', ')}
                  </div>
                )}
                {m.processingTime && <div className="meta">{m.processingTime}ms</div>}
              </div>
            ))}
            {loading && <div className="message assistant"><div className="content">Thinking...</div></div>}
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
            <button onClick={sendQuery} disabled={loading}>Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
