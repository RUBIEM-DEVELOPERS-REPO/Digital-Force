'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Sidebar from '@/components/Sidebar'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle2, XCircle, Clock, Activity, AlertCircle,
  ArrowLeft, Bot, Loader2, ChevronDown, ChevronUp,
  Target, Calendar, Zap, TrendingUp
} from 'lucide-react'
import api, { Goal as ApiGoal } from '@/lib/api'
import { getToken } from '@/lib/auth'

const AGENT_COLORS: Record<string, string> = {
  orchestrator:     '#F59E0B',
  researcher:       '#3B82F6',
  strategist:       '#8B5CF6',
  content_director: '#EC4899',
  visual_designer:  '#10B981',
  publisher:        '#00A3FF',
  skillforge:       '#F97316',
  monitor:          '#22D3EE',
  human:            '#F8FAFC',
}

const AGENT_INITIALS: Record<string, string> = {
  orchestrator: 'OR', researcher: 'RE', strategist: 'ST',
  content_director: 'CD', visual_designer: 'VD',
  publisher: 'PB', skillforge: 'SF', monitor: 'MN', human: 'HU',
}

const AGENT_LABELS: Record<string, string> = {
  orchestrator: 'Orchestrator', researcher: 'Researcher', strategist: 'Strategist',
  content_director: 'Content Director', visual_designer: 'Visual Designer',
  publisher: 'Publisher', skillforge: 'SkillForge', monitor: 'Monitor', human: 'Human',
}

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  planning:          { label: 'Synthesizing', color: '#33BAFF', bg: 'rgba(0,163,255,0.1)' },
  awaiting_approval: { label: 'Authorization Required', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  executing:         { label: 'Executing', color: '#34D399', bg: 'rgba(16,185,129,0.1)' },
  monitoring:        { label: 'Monitoring', color: '#22D3EE', bg: 'rgba(34,211,238,0.1)' },
  complete:          { label: 'Complete', color: '#34D399', bg: 'rgba(16,185,129,0.08)' },
  failed:            { label: 'Failed', color: '#F87171', bg: 'rgba(239,68,68,0.1)' },
}

interface AgentLogEntry {
  id: string; agent: string; level: string;
  thought: string; action?: string; created_at: string
}

type Goal = ApiGoal

export default function GoalDetailPage() {
  const { id } = useParams() as { id: string }
  const [goal, setGoal] = useState<Goal | null>(null)
  const [logs, setLogs] = useState<AgentLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [approving, setApproving] = useState(false)
  const [notes, setNotes] = useState('')
  const [showPlan, setShowPlan] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)

  const fetchGoal = async () => {
    try {
      const data = await api.goals.get(id)
      setGoal(data)
      setLogs(data.agent_logs || [])
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchGoal().finally(() => setLoading(false))
    const interval = setInterval(fetchGoal, 3000)
    return () => clearInterval(interval)
  }, [id])

  // SSE for live logs
  useEffect(() => {
    const token = getToken()
    const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const url = `${BASE}/api/stream/goals/${id}${token ? `?token=${token}` : ''}`
    const es = new EventSource(url)
    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        if (event.type === 'agent_log') {
          setLogs(prev => {
            const exists = prev.some(l => l.thought === event.thought && l.agent === event.agent)
            if (exists) return prev
            return [...prev, { id: Math.random().toString(), agent: event.agent, level: event.level, thought: event.thought, action: event.action, created_at: event.timestamp }].slice(-100)
          })
          logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
      } catch {}
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [id])

  const handleApprove = async (approved: boolean) => {
    setApproving(true)
    try {
      await api.goals.approve(id, { approved, notes: notes || undefined })
      await fetchGoal()
    } catch (e) { console.error(e) }
    finally { setApproving(false) }
  }

  if (loading) return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 flex items-center justify-center" style={{ background: '#080B12' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
        </div>
      </main>
    </div>
  )

  if (!goal) return null

  const isActive = ['planning', 'executing', 'monitoring'].includes(goal.status)
  const needsApproval = goal.status === 'awaiting_approval'
  const statusCfg = STATUS_MAP[goal.status] || { label: goal.status, color: '#94A3B8', bg: 'rgba(148,163,184,0.1)' }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* ── Sticky top bar ── */}
        <div style={{
          position: 'sticky', top: 0, zIndex: 20,
          padding: '1rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.04)',
          background: 'rgba(8,11,18,0.9)', backdropFilter: 'blur(20px)',
          display: 'flex', alignItems: 'center', gap: '1rem',
        }}>
          <Link href="/goals" style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '0.45rem 0.875rem', borderRadius: 8, textDecoration: 'none',
            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)',
            color: '#64748B', fontSize: '0.8rem', fontWeight: 600, transition: 'color 0.2s',
          }}
            onMouseEnter={e => (e.currentTarget.style.color = '#94A3B8')}
            onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}>
            <ArrowLeft size={14} /> Tasks
          </Link>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, color: '#E2E8F0', fontSize: '0.95rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: '-0.01em' }}>
              {goal.title}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0.3rem 0.875rem', borderRadius: 8, background: statusCfg.bg, border: `1px solid ${statusCfg.color}30` }}>
            {isActive && <span style={{ width: 6, height: 6, borderRadius: '50%', background: statusCfg.color, boxShadow: `0 0 8px ${statusCfg.color}` }} />}
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: statusCfg.color, letterSpacing: '0.06em' }}>{statusCfg.label.toUpperCase()}</span>
          </div>
        </div>

        <div style={{ padding: '2rem', display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem' }}>

          {/* ── Left column ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            {/* Progress card */}
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              style={{ padding: '1.5rem', borderRadius: '1rem', background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Target size={17} style={{ color: '#33BAFF' }} />
                  </div>
                  <span style={{ fontWeight: 700, color: '#E2E8F0', fontSize: '0.9rem' }}>Mission Progress</span>
                </div>
                <span style={{ fontSize: '2rem', fontWeight: 900, color: '#F8FAFC', letterSpacing: '-0.05em' }}>{Math.round(goal.progress_percent)}%</span>
              </div>
              <div className="progress-bar" style={{ marginBottom: '0.875rem' }}>
                <div className="progress-fill" style={{ width: `${goal.progress_percent}%` }} />
              </div>
              <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.04em' }}>
                <span style={{ color: '#34D399' }}>{goal.tasks_completed} COMPLETE</span>
                <span style={{ color: '#475569' }}>{goal.tasks_total - goal.tasks_completed - (goal.tasks_failed || 0)} PENDING</span>
                {(goal.tasks_failed || 0) > 0 && <span style={{ color: '#F87171' }}>{goal.tasks_failed} FAILED</span>}
              </div>
            </motion.div>

            {/* Authorization panel */}
            {needsApproval && goal.plan && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                style={{
                  padding: '1.75rem', borderRadius: '1rem',
                  background: 'linear-gradient(135deg, rgba(245,158,11,0.06), rgba(15,23,42,0.4))',
                  border: '1px solid rgba(245,158,11,0.3)', backdropFilter: 'blur(12px)',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.25rem' }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <AlertCircle size={18} style={{ color: '#F59E0B' }} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, color: '#F8FAFC', fontSize: '0.95rem', letterSpacing: '-0.01em' }}>Authorization Required</div>
                    <div style={{ fontSize: '0.72rem', color: '#78350F', fontWeight: 600, letterSpacing: '0.04em', marginTop: 2 }}>Review the tactical plan before execution commences</div>
                  </div>
                </div>

                <div style={{ padding: '1.125rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)', marginBottom: '1.25rem' }}>
                  <div style={{ fontWeight: 700, color: '#E2E8F0', fontSize: '0.9rem', marginBottom: '0.5rem' }}>{goal.plan.campaign_name}</div>
                  <p style={{ fontSize: '0.82rem', color: '#64748B', lineHeight: 1.7, marginBottom: '0.875rem' }}>{goal.plan.campaign_summary}</p>
                  <div style={{ display: 'flex', gap: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.72rem', fontWeight: 700, color: '#475569', letterSpacing: '0.04em' }}>
                      <Zap size={12} style={{ color: '#F59E0B' }} />{goal.plan.tasks?.length || 0} OPERATIONS PLANNED
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.72rem', fontWeight: 700, color: '#475569', letterSpacing: '0.04em' }}>
                      <Calendar size={12} style={{ color: '#F59E0B' }} />{goal.plan.duration_days || 7} DAYS
                    </div>
                  </div>
                </div>

                <textarea className="df-textarea" style={{ marginBottom: '1rem', minHeight: 70 }}
                  placeholder="Add strategic notes or modifications (optional)..."
                  value={notes} onChange={e => setNotes(e.target.value)} />

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button onClick={() => handleApprove(true)} disabled={approving}
                    style={{
                      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                      padding: '0.9rem', borderRadius: '0.875rem',
                      background: 'linear-gradient(135deg, #00A3FF, #006199)',
                      border: '1px solid rgba(255,255,255,0.15)', color: '#fff',
                      fontSize: '0.9rem', fontWeight: 800, cursor: approving ? 'not-allowed' : 'pointer',
                      boxShadow: '0 8px 32px rgba(0,163,255,0.35)', letterSpacing: '0.02em',
                      opacity: approving ? 0.7 : 1, transition: 'opacity 0.2s',
                    }}>
                    {approving ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <CheckCircle2 size={16} />}
                    Authorize & Execute
                  </button>
                  <button onClick={() => handleApprove(false)} disabled={approving}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '0.9rem 1.5rem', borderRadius: '0.875rem',
                      background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                      color: '#F87171', fontSize: '0.9rem', fontWeight: 700, cursor: approving ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s', opacity: approving ? 0.7 : 1,
                    }}>
                    <XCircle size={16} /> Revise
                  </button>
                </div>
              </motion.div>
            )}

            {/* Campaign task list */}
            {goal.plan?.tasks && goal.plan.tasks.length > 0 && !needsApproval && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                style={{ borderRadius: '1rem', overflow: 'hidden', background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)', border: '1px solid rgba(255,255,255,0.04)' }}>
                <button onClick={() => setShowPlan(p => !p)}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.125rem 1.5rem', background: 'none', border: 'none', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Activity size={15} style={{ color: '#33BAFF' }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#E2E8F0', letterSpacing: '0.02em' }}>
                      Tactical Ops Plan <span style={{ color: '#475569', fontWeight: 600 }}>({goal.plan.tasks.length})</span>
                    </span>
                  </div>
                  {showPlan ? <ChevronUp size={15} style={{ color: '#475569' }} /> : <ChevronDown size={15} style={{ color: '#475569' }} />}
                </button>

                <AnimatePresence>
                  {showPlan && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      style={{ borderTop: '1px solid rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                      {goal.plan.tasks.slice(0, 20).map((task, i) => (
                        <div key={task.id || i} style={{
                          padding: '0.875rem 1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem',
                          borderBottom: i < Math.min(goal.plan!.tasks!.length, 20) - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
                        }}>
                          <div style={{ width: 22, height: 22, borderRadius: 6, background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                            <span style={{ fontSize: '0.6rem', fontWeight: 900, color: '#33BAFF' }}>{i + 1}</span>
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '0.85rem', color: '#CBD5E1', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 5 }}>{task.title}</div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px', borderRadius: 4, background: 'rgba(0,163,255,0.08)', color: '#33BAFF', letterSpacing: '0.04em' }}>
                                {task.platform?.toUpperCase()}
                              </span>
                              <span style={{ fontSize: '0.65rem', fontWeight: 600, padding: '2px 8px', borderRadius: 4, background: 'rgba(255,255,255,0.04)', color: '#64748B', letterSpacing: '0.03em' }}>
                                {task.content_type}
                              </span>
                              {task.scheduled_at && (
                                <span style={{ fontSize: '0.65rem', color: '#334155', fontWeight: 600 }}>
                                  {new Date(task.scheduled_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </div>

          {/* ── Right column: Agent Feed ── */}
          <div style={{ position: 'sticky', top: '5rem', height: 'calc(100vh - 7rem)' }}>
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
              style={{
                height: '100%', display: 'flex', flexDirection: 'column', borderRadius: '1rem',
                background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)',
                border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)', overflow: 'hidden',
              }}>
              {/* Feed header */}
              <div style={{ padding: '1.125rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Bot size={15} style={{ color: '#33BAFF' }} />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#E2E8F0', letterSpacing: '-0.01em' }}>Agent Feed</div>
                  <div style={{ fontSize: '0.65rem', color: '#334155', fontWeight: 600, letterSpacing: '0.05em' }}>LIVE TELEMETRY</div>
                </div>
                {isActive && (
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 5 }}>
                    <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                  </div>
                )}
              </div>

              {/* Log entries */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                {logs.length === 0 ? (
                  <div style={{ padding: '3rem 1rem', textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginBottom: '0.875rem' }}>
                      <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                    </div>
                    <p style={{ fontSize: '0.78rem', color: '#334155', fontWeight: 600 }}>Awaiting agent telemetry...</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                    {logs.map((log, i) => {
                      const color = AGENT_COLORS[log.agent] || '#94A3B8'
                      const label = AGENT_LABELS[log.agent] || log.agent
                      const initials = AGENT_INITIALS[log.agent] || log.agent.slice(0, 2).toUpperCase()
                      return (
                        <div key={log.id || i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                          <div style={{ width: 26, height: 26, borderRadius: 8, flexShrink: 0, background: `${color}15`, border: `1px solid ${color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <span style={{ fontSize: '0.58rem', fontWeight: 900, color }}>{initials}</span>
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                              <span style={{ fontSize: '0.72rem', fontWeight: 700, color }}>{label}</span>
                              <span style={{ fontSize: '0.62rem', color: '#334155', fontWeight: 500 }}>
                                {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                              </span>
                            </div>
                            <p style={{ fontSize: '0.78rem', color: '#64748B', lineHeight: 1.6, margin: 0 }}>{log.thought}</p>
                            {log.action && (
                              <div style={{ marginTop: 4, padding: '2px 8px', borderRadius: 4, background: 'rgba(0,163,255,0.06)', border: '1px solid rgba(0,163,255,0.12)', display: 'inline-block' }}>
                                <span style={{ fontSize: '0.65rem', color: '#33BAFF', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{log.action}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}
