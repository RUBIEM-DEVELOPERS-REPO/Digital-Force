'use client'

import { useState, useEffect, useRef, useCallback, KeyboardEvent } from 'react'
import Sidebar from '@/components/Sidebar'
import { Send, Trash2, Bot, User, Zap, MessageSquare } from 'lucide-react'
import { getToken } from '@/lib/auth'
import api from '@/lib/api'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ─── Types ─────────────────────────────────────────────────

interface Chip {
  type: 'thinking' | 'action'
  content: string
}

interface Bubble {
  id: string
  content: string
  isStreaming: boolean
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'agent'
  agentName?: string
  bubbles: Bubble[]
  chips: Chip[]
  created_at: string
}

// ─── Agent visual config ────────────────────────────────────

const AGENT_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  orchestrator:     { emoji: '🎯', label: 'Orchestrator',     color: '#F59E0B' },
  researcher:       { emoji: '🔍', label: 'Researcher',       color: '#3B82F6' },
  strategist:       { emoji: '📋', label: 'Strategist',       color: '#8B5CF6' },
  content_director: { emoji: '✍️',  label: 'Content Director', color: '#EC4899' },
  publisher:        { emoji: '📤', label: 'Publisher',        color: '#10B981' },
  skillforge:       { emoji: '⚡', label: 'SkillForge',       color: '#F97316' },
  monitor:          { emoji: '📊', label: 'Monitor',          color: '#06B6D4' },
}

const SUGGESTED_PROMPTS = [
  'Create a 2-week LinkedIn campaign for a SaaS product',
  'What campaigns are currently active and how are they performing?',
  'Show me what\'s scheduled for this week',
  'Replan my top campaign with more video content',
  'Which platform is delivering the best results?',
]

// ─── Helper: convert a DB history record to a Message ──────

function historyToMessage(h: { id: string; role: string; content: string; agent_name?: string; created_at: string }): Message {
  return {
    id: h.id,
    role: h.role as 'user' | 'assistant' | 'agent',
    agentName: h.agent_name || undefined,
    bubbles: [{ id: `${h.id}-b0`, content: h.content, isStreaming: false }],
    chips: [],
    created_at: h.created_at,
  }
}

// ─── Main component ─────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages]         = useState<Message[]>([])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [lastPollTime, setLastPollTime] = useState<string | null>(null)
  const [agentsActive, setAgentsActive] = useState(false)

  const bottomRef    = useRef<HTMLDivElement>(null)
  const textareaRef  = useRef<HTMLTextAreaElement>(null)

  // ── Load history on mount ─────────────────────────────────
  useEffect(() => {
    api.chat.history()
      .then(history => {
        if (history.length > 0) {
          setMessages(history.map(historyToMessage))
          // Seed the poll time from the last message
          const lastTs = history[history.length - 1].created_at
          setLastPollTime(lastTs)
        }
        setHistoryLoaded(true)
      })
      .catch(() => setHistoryLoaded(true))
  }, [])

  // ── Auto-scroll ───────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Agent push polling (every 10 s + immediately on mount) ──────────────
  useEffect(() => {
    if (!historyLoaded) return

    const pollUpdates = async () => {
      try {
        const data = await api.chat.updates(lastPollTime || undefined)
        setAgentsActive(data.agents_active)
        
        if (data.messages && data.messages.length > 0) {
          setMessages(prev => {
            const existingIds = new Set(prev.map(m => m.id))
            const newOnes = data.messages
              .filter(u => !existingIds.has(u.id))
              .map(historyToMessage)
            return newOnes.length > 0 ? [...prev, ...newOnes] : prev
          })
          setLastPollTime(data.messages[data.messages.length - 1].created_at)
        }
      } catch { /* silent */ }
    }

    // Fire immediately then every 10s
    pollUpdates()
    const poll = setInterval(pollUpdates, 10_000)
    return () => clearInterval(poll)
  }, [historyLoaded])

  // ── Send a message ────────────────────────────────────────
  const sendMessage = useCallback(async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    setInput('')
    setLoading(true)

    const now = new Date().toISOString()

    // Push user message immediately
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      bubbles: [{ id: `u-${Date.now()}-b0`, content: msg, isStreaming: false }],
      chips: [],
      created_at: now,
    }

    // Placeholder assistant message
    const assistantId = `a-${Date.now()}`
    const firstBubbleId = `${assistantId}-b0`
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      bubbles: [{ id: firstBubbleId, content: '', isStreaming: true }],
      chips: [],
      created_at: now,
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])

    try {
      const token = getToken()
      const response = await fetch(`${BASE}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: msg, context: {} }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader  = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      // Track which bubble in the assistant message is currently streaming
      let activeBubbleId = firstBubbleId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const chunk = JSON.parse(line.slice(6))

            if (chunk.type === 'done') break

            if (chunk.type === 'thinking' || chunk.type === 'action') {
              // Append chip to the assistant message
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, chips: [...m.chips, { type: chunk.type, content: chunk.content }] }
                  : m
              ))
            }

            else if (chunk.type === 'bubble_start') {
              const newBubbleId: string = chunk.bubble_id || `${assistantId}-b${Date.now()}`
              activeBubbleId = newBubbleId
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantId) return m
                // Don't add a duplicate if it's the initial placeholder bubble
                const alreadyExists = m.bubbles.some(b => b.id === newBubbleId)
                if (alreadyExists) return m
                // If the initial placeholder is still empty, repurpose it
                if (m.bubbles.length === 1 && m.bubbles[0].content === '' && m.bubbles[0].id === firstBubbleId) {
                  return { ...m, bubbles: [{ id: newBubbleId, content: '', isStreaming: true }] }
                }
                return { ...m, bubbles: [...m.bubbles, { id: newBubbleId, content: '', isStreaming: true }] }
              }))
            }

            else if (chunk.type === 'message') {
              // Stream tokens into the active bubble
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantId) return m
                return {
                  ...m,
                  bubbles: m.bubbles.map(b =>
                    b.id === activeBubbleId
                      ? { ...b, content: b.content + (chunk.content || '') }
                      : b
                  ),
                }
              }))
            }

            else if (chunk.type === 'bubble_end') {
              // Mark current bubble as done streaming
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantId) return m
                return {
                  ...m,
                  bubbles: m.bubbles.map(b =>
                    b.id === activeBubbleId ? { ...b, isStreaming: false } : b
                  ),
                }
              }))
            }

            else if (chunk.type === 'error') {
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, bubbles: [{ id: firstBubbleId, content: chunk.content, isStreaming: false }] }
                  : m
              ))
            }

          } catch { /* skip malformed */ }
        }
      }
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, bubbles: [{ id: firstBubbleId, content: 'Connection error. Check Settings and try again.', isStreaming: false }] }
          : m
      ))
    } finally {
      // Finalize all streaming bubbles
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, bubbles: m.bubbles.map(b => ({ ...b, isStreaming: false })) }
          : m
      ))
      setLoading(false)
      // Update poll time so we don't re-fetch our own assistant message
      setLastPollTime(new Date().toISOString())
    }
  }, [input, loading])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearHistory = async () => {
    await api.chat.clearHistory()
    setMessages([])
    setLastPollTime(null)
  }

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // ── Typing dots component ─────────────────────────────────
  const TypingDots = () => (
    <span style={{ display: 'inline-flex', gap: 3, alignItems: 'center', padding: '2px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} className="thinking-dot" style={{
          width: 6, height: 6,
          animationDelay: `${i * 0.15}s`,
        }} />
      ))}
    </span>
  )

  // ── Render a single message row ───────────────────────────
  const renderMessage = (msg: Message) => {
    const isUser   = msg.role === 'user'
    const isAgent  = msg.role === 'agent'
    const agentCfg = isAgent && msg.agentName ? AGENT_CONFIG[msg.agentName] : null

    return (
      <div key={msg.id} style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        gap: 10,
      }}>
        {/* Avatar */}
        <div style={{
          width: 32, height: 32, borderRadius: 10, flexShrink: 0,
          background: isUser
            ? 'rgba(167,139,250,0.15)'
            : isAgent && agentCfg
              ? `${agentCfg.color}22`
              : 'linear-gradient(135deg, #7C3AED, #4F46E5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: isUser
            ? '1px solid rgba(167,139,250,0.25)'
            : isAgent && agentCfg
              ? `1px solid ${agentCfg.color}44`
              : 'none',
          fontSize: isAgent ? '14px' : undefined,
        }}>
          {isUser
            ? <User size={14} style={{ color: '#A78BFA' }} />
            : isAgent && agentCfg
              ? agentCfg.emoji
              : <Bot size={14} color="white" />
          }
        </div>

        {/* Content column */}
        <div style={{ maxWidth: '75%', minWidth: 60, display: 'flex', flexDirection: 'column', gap: 6 }}>

          {/* Agent badge */}
          {isAgent && agentCfg && (
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.05em',
              color: agentCfg.color,
              paddingBottom: 2,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: agentCfg.color,
                boxShadow: `0 0 6px ${agentCfg.color}`,
              }} />
              {agentCfg.label.toUpperCase()}
            </div>
          )}

          {/* Thinking / action chips */}
          {msg.chips.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {msg.chips.map((chip, i) => (
                <div key={i} style={{
                  fontSize: '0.72rem', padding: '0.25rem 0.55rem',
                  borderRadius: 6, display: 'inline-flex', alignItems: 'center', gap: 5,
                  background: chip.type === 'action' ? 'rgba(34,211,238,0.08)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${chip.type === 'action' ? 'rgba(34,211,238,0.2)' : 'rgba(255,255,255,0.07)'}`,
                  color: chip.type === 'action' ? '#22D3EE' : 'rgba(255,255,255,0.4)',
                }}>
                  {chip.type === 'action' ? '⚙️' : '💭'} {chip.content}
                </div>
              ))}
            </div>
          )}

          {/* Bubbles */}
          {msg.bubbles.map((bubble, bi) => (
            <div key={bubble.id}>
              {isUser ? (
                <div style={{
                  padding: '0.75rem 1rem', borderRadius: 14,
                  background: 'linear-gradient(135deg, rgba(124,58,237,0.35), rgba(79,70,229,0.28))',
                  border: '1px solid rgba(124,58,237,0.3)',
                  color: '#fff', fontSize: '0.9rem', lineHeight: 1.65, whiteSpace: 'pre-wrap',
                }}>
                  {bubble.content}
                </div>
              ) : (
                <div style={{
                  padding: '0.875rem 1.125rem', borderRadius: 14,
                  background: isAgent && agentCfg
                    ? `rgba(${hexToRgb(agentCfg.color)}, 0.05)`
                    : 'rgba(255,255,255,0.05)',
                  border: isAgent && agentCfg
                    ? `1px solid ${agentCfg.color}30`
                    : '1px solid rgba(255,255,255,0.07)',
                  color: '#fff', fontSize: '0.9rem', lineHeight: 1.65, whiteSpace: 'pre-wrap',
                }}>
                  {bubble.content || (bubble.isStreaming ? <TypingDots /> : '')}
                  {bubble.isStreaming && bubble.content && (
                    <span style={{ display: 'inline-flex', gap: 3, marginLeft: 4, verticalAlign: 'middle' }}>
                      <TypingDots />
                    </span>
                  )}
                </div>
              )}

              {/* Inter-bubble typing indicator (between bubbles within one response) */}
              {!isUser && bubble.isStreaming === false && bi < msg.bubbles.length - 1 &&
               msg.bubbles[bi + 1]?.isStreaming && (
                <div style={{
                  padding: '0.6rem 1rem', borderRadius: 14, marginTop: 6,
                  background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
                  display: 'inline-flex',
                }}>
                  <TypingDots />
                </div>
              )}
            </div>
          ))}

          {/* Timestamp */}
          <div style={{
            fontSize: '0.68rem', color: 'rgba(255,255,255,0.22)',
            textAlign: isUser ? 'right' : 'left',
          }}>
            {formatTime(msg.created_at)}
          </div>
        </div>
      </div>
    )
  }

  // ─────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'rgba(255,255,255,0.02)', backdropFilter: 'blur(10px)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'linear-gradient(135deg, #7C3AED, #4F46E5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 20px rgba(124,58,237,0.35)',
            }}>
              <Zap size={18} color="white" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: '#fff' }}>ASMIA</div>
              <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.35)' }}>
                Autonomous Social Media Intelligence Agency
              </div>
            </div>
          </div>
          {messages.length > 0 && (
            <button id="clear-history" onClick={clearHistory}
              className="btn-ghost" style={{ fontSize: '0.8rem', gap: 6 }}>
              <Trash2 size={14} /> Clear history
            </button>
          )}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {historyLoaded && messages.length === 0 ? (
            <div style={{ maxWidth: 620, margin: '3rem auto', textAlign: 'center' }}>
              <div style={{
                width: 72, height: 72, borderRadius: 20,
                background: 'rgba(124,58,237,0.1)', border: '1px solid rgba(124,58,237,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 1.5rem',
              }}>
                <MessageSquare size={32} style={{ color: '#A78BFA' }} />
              </div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', marginBottom: 8 }}>
                Talk to your agency
              </h2>
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.9rem', marginBottom: '2rem', lineHeight: 1.6 }}>
                Brief ASMIA in plain English. The agents take it from there — planning, creating,
                publishing, and reporting back here automatically.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {SUGGESTED_PROMPTS.map((p, i) => (
                  <button key={i} id={`prompt-${i}`} onClick={() => sendMessage(p)}
                    style={{
                      padding: '0.75rem 1rem', borderRadius: 12, textAlign: 'left',
                      background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
                      color: 'rgba(255,255,255,0.6)', fontSize: '0.875rem', cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = 'rgba(124,58,237,0.12)'
                      e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'
                      e.currentTarget.style.color = '#fff'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
                      e.currentTarget.style.color = 'rgba(255,255,255,0.6)'
                    }}>
                    "{p}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ maxWidth: 820, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {messages.map(renderMessage)}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Agents Working Indicator */}
        {agentsActive && !loading && (
          <div style={{
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            padding: '8px 0 0 0', position: 'relative', zIndex: 10
          }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              background: 'rgba(34, 211, 238, 0.1)', border: '1px solid rgba(34, 211, 238, 0.2)',
              borderRadius: 20, padding: '4px 16px', fontSize: '0.75rem', color: '#22D3EE',
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
              boxShadow: '0 0 10px rgba(34, 211, 238, 0.2)'
            }}>
              <span className="thinking-dot" style={{ width: 6, height: 6, background: '#22D3EE' }} />
              agents working...
            </div>
            <style jsx>{`
              @keyframes pulse {
                0%, 100% { opacity: 1; border-color: rgba(34, 211, 238, 0.4); }
                50% { opacity: 0.6; border-color: rgba(34, 211, 238, 0.1); }
              }
            `}</style>
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: '1rem 1.5rem 1.25rem',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(255,255,255,0.02)',
          flexShrink: 0,
        }}>
          <div style={{ maxWidth: 820, margin: '0 auto' }}>
            <div style={{
              display: 'flex', gap: 10, alignItems: 'flex-end',
              background: 'rgba(255,255,255,0.05)',
              border: `1px solid ${loading ? 'rgba(124,58,237,0.35)' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: 16, padding: '0.5rem 0.5rem 0.5rem 1rem',
              transition: 'border-color 0.2s',
            }}>
              <textarea
                ref={textareaRef}
                id="chat-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={loading ? 'ASMIA is responding...' : 'Brief the agency... (Enter to send)'}
                disabled={loading}
                rows={1}
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none',
                  color: '#fff', fontSize: '0.9rem', lineHeight: 1.5, resize: 'none',
                  minHeight: 24, maxHeight: 120, fontFamily: 'inherit',
                  opacity: loading ? 0.5 : 1,
                }}
                onInput={e => {
                  const t = e.target as HTMLTextAreaElement
                  t.style.height = 'auto'
                  t.style.height = Math.min(t.scrollHeight, 120) + 'px'
                }}
              />
              <button
                id="send-chat"
                onClick={() => sendMessage()}
                disabled={loading || !input.trim()}
                style={{
                  width: 40, height: 40, borderRadius: 12, flexShrink: 0,
                  background: input.trim() && !loading
                    ? 'linear-gradient(135deg, #7C3AED, #4F46E5)'
                    : 'rgba(255,255,255,0.06)',
                  border: 'none',
                  cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.2s',
                  boxShadow: input.trim() && !loading ? '0 0 20px rgba(124,58,237,0.35)' : 'none',
                }}>
                <Send size={16} color={input.trim() && !loading ? 'white' : 'rgba(255,255,255,0.3)'} />
              </button>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', textAlign: 'center', marginTop: 8 }}>
              ASMIA agents work autonomously — updates appear here in real time
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Utility ───────────────────────────────────────────────
function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}
