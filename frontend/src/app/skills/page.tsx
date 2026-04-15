'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Sidebar from '@/components/Sidebar'
import { Cpu, Code, ToggleLeft, ToggleRight, Trash2, Zap, ChevronDown, ChevronUp, CheckCircle2, XCircle } from 'lucide-react'
import api from '@/lib/api'

interface Skill {
  id: string; name: string; display_name: string; description: string
  code?: string; test_passed: boolean; usage_count: number
  is_active: boolean; sandbox_test_result?: string; created_at: string
}

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.07 } } },
  item: { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: [0.4,0,0.2,1] } } },
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    api.skills.list().then(setSkills).finally(() => setLoading(false))
  }, [])

  const toggleSkill = async (id: string) => {
    const res = await api.skills.toggle(id)
    setSkills(prev => prev.map(s => s.id === id ? { ...s, is_active: res.is_active } : s))
  }

  const deleteSkill = async (id: string) => {
    await api.skills.delete(id)
    setSkills(prev => prev.filter(s => s.id !== id))
  }

  const loadCode = async (id: string) => {
    if (expanded === id) { setExpanded(null); return }
    const skill = await api.skills.get(id)
    setSkills(prev => prev.map(s => s.id === id ? { ...s, code: skill.code, sandbox_test_result: skill.sandbox_test_result } : s))
    setExpanded(id)
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* ── Header ── */}
        <div style={{ padding: '3rem 3rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
              DIGITAL FORCE — NEURAL CAPABILITIES
            </div>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.035em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, marginBottom: '0.625rem' }}>
              SkillForge
            </h1>
            <p style={{ fontSize: '0.875rem', color: '#475569' }}>
              Autonomously synthesized capabilities — sandbox-validated before every activation
            </p>
          </motion.div>
        </div>

        <div style={{ padding: '2rem 3rem' }}>

          {/* ── Stats ── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
            {[
              { label: 'Total Capabilities', value: skills.length, color: '#00A3FF' },
              { label: 'Active', value: skills.filter(s => s.is_active).length, color: '#10B981' },
              { label: 'Total Executions', value: skills.reduce((a, s) => a + s.usage_count, 0), color: '#22D3EE' },
            ].map((s, i) => (
              <div key={i} style={{
                padding: '1.5rem', borderRadius: '1rem', display: 'flex', alignItems: 'center', gap: '1rem',
                background: 'linear-gradient(135deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%)',
                border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)',
              }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 900, color: s.color, letterSpacing: '-0.04em', lineHeight: 1 }}>{s.value}</div>
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#475569', letterSpacing: '0.06em' }}>{s.label.toUpperCase()}</div>
              </div>
            ))}
          </motion.div>

          {/* ── Skills List ── */}
          {loading ? (
            <div style={{ padding: '5rem', display: 'flex', justifyContent: 'center', borderRadius: '1rem', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.03)' }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
              </div>
            </div>
          ) : skills.length === 0 ? (
            <div style={{ padding: '6rem 2rem', textAlign: 'center', borderRadius: '1.25rem', border: '1px dashed rgba(0,163,255,0.1)', background: 'rgba(0,163,255,0.02)' }}>
              <div style={{ width: 64, height: 64, borderRadius: '1.125rem', background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.25rem' }}>
                <Zap size={28} style={{ color: '#00A3FF' }} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#475569', marginBottom: '0.5rem' }}>No capabilities forged yet</h3>
              <p style={{ fontSize: '0.82rem', color: '#334155', maxWidth: 400, margin: '0 auto', lineHeight: 1.7 }}>
                When agents encounter challenges requiring novel solutions, they autonomously synthesize and register new capabilities here.
              </p>
            </div>
          ) : (
            <motion.div variants={stagger.container} initial="hidden" animate="show" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {skills.map(skill => (
                <motion.div key={skill.id} variants={stagger.item}
                  style={{
                    borderRadius: '1rem', overflow: 'hidden',
                    background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)',
                    border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)',
                    transition: 'border-color 0.2s',
                    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(0,163,255,0.2)')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.04)')}>

                  {/* Card body */}
                  <div style={{ padding: '1.375rem 1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1.25rem' }}>
                    {/* Icon */}
                    <div style={{
                      width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                      background: skill.test_passed ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                      border: `1px solid ${skill.test_passed ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Code size={20} style={{ color: skill.test_passed ? '#34D399' : '#F87171' }} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#F8FAFC', letterSpacing: '-0.01em' }}>{skill.display_name}</span>
                        <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.04)', color: '#475569', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.04em' }}>
                          {skill.name}
                        </span>
                        {skill.test_passed
                          ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: 'rgba(16,185,129,0.1)', color: '#34D399', letterSpacing: '0.04em' }}><CheckCircle2 size={11} /> VALIDATED</span>
                          : <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: 'rgba(239,68,68,0.1)', color: '#F87171', letterSpacing: '0.04em' }}><XCircle size={11} /> UNVERIFIED</span>
                        }
                        {skill.is_active && (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.68rem', fontWeight: 700, padding: '2px 8px', borderRadius: 5, background: 'rgba(0,163,255,0.1)', color: '#33BAFF', letterSpacing: '0.04em' }}>
                            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00A3FF', boxShadow: '0 0 6px #00A3FF' }} />
                            LIVE
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: '0.82rem', color: '#64748B', lineHeight: 1.6, marginBottom: '0.625rem' }}>{skill.description}</p>
                      <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 600, letterSpacing: '0.04em' }}>
                        {skill.usage_count} executions · {new Date(skill.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </div>
                    </div>

                    {/* Controls */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                      <button onClick={() => loadCode(skill.id)}
                        style={{ width: 34, height: 34, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', cursor: 'pointer', color: '#64748B', transition: 'color 0.2s' }}
                        onMouseEnter={e => (e.currentTarget.style.color = '#94A3B8')}
                        onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}>
                        {expanded === skill.id ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                      </button>
                      <button onClick={() => toggleSkill(skill.id)}
                        style={{ width: 34, height: 34, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: skill.is_active ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${skill.is_active ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.06)'}`, cursor: 'pointer', transition: 'all 0.2s' }}>
                        {skill.is_active
                          ? <ToggleRight size={18} style={{ color: '#34D399' }} />
                          : <ToggleLeft size={18} style={{ color: '#475569' }} />
                        }
                      </button>
                      <button onClick={() => deleteSkill(skill.id)}
                        style={{ width: 34, height: 34, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.12)', cursor: 'pointer', color: '#F87171', opacity: 0.5, transition: 'opacity 0.2s' }}
                        onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                        onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Code Viewer */}
                  {expanded === skill.id && skill.code && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                      style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                      <pre style={{
                        padding: '1.5rem', fontSize: '0.78rem', overflowX: 'auto', fontFamily: 'JetBrains Mono, monospace',
                        color: '#33BAFF', background: 'rgba(0,0,0,0.25)', maxHeight: 320, lineHeight: 1.7, margin: 0,
                      }}>
                        {skill.code}
                      </pre>
                      {skill.sandbox_test_result && (
                        <div style={{ padding: '0.875rem 1.5rem', borderTop: '1px solid rgba(255,255,255,0.03)', background: 'rgba(16,185,129,0.03)' }}>
                          <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#334155', letterSpacing: '0.08em', marginBottom: 6 }}>SANDBOX OUTPUT</div>
                          <div style={{ fontSize: '0.78rem', color: '#34D399', fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.6 }}>{skill.sandbox_test_result}</div>
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* Glowing progress bar along the card bottom */}
                  <div style={{ height: 2, background: 'rgba(255,255,255,0.03)', position: 'relative' }}>
                    <div style={{
                      position: 'absolute', left: 0, top: 0, bottom: 0,
                      width: skill.is_active ? '100%' : '20%',
                      background: skill.is_active ? 'linear-gradient(90deg, #00A3FF, #22D3EE)' : 'rgba(71,85,105,0.5)',
                      boxShadow: skill.is_active ? '0 0 8px rgba(34,211,238,0.8)' : 'none',
                      transition: 'width 0.6s ease, box-shadow 0.3s',
                    }} />
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}
