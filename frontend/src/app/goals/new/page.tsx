'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '@/components/Sidebar'
import { Send, Target, Calendar, Zap, Loader2, AlertCircle, ChevronRight } from 'lucide-react'
import api from '@/lib/api'

const PLATFORM_OPTIONS = [
  { id: 'linkedin',  label: 'LinkedIn'  },
  { id: 'facebook',  label: 'Facebook'  },
  { id: 'twitter',   label: 'X/Twitter' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'tiktok',    label: 'TikTok'    },
  { id: 'youtube',   label: 'YouTube'   },
]

const EXAMPLES = [
  'Schedule 50 Facebook posts of our summit flyers across this week, starting tomorrow',
  'Grow our LinkedIn following from 1,000 to 5,000 in the next 30 days',
  'Post our 10 product videos across TikTok, Instagram, and YouTube',
  'Run a 2-week awareness campaign using assets from the Knowledge Core',
  'Create a thought leadership series on LinkedIn for our CEO, 1 post per day for 7 days',
]

const THINKING_STEPS = [
  'Parsing directive and extracting strategic intent...',
  'Cross-referencing market intelligence and audience data...',
  'Synthesizing multi-platform campaign architecture...',
  'Generating tactical operation sequences...',
  'Awaiting your authorization to execute...',
]

export default function NewGoalPage() {
  const router = useRouter()
  const [description, setDescription] = useState('')
  const [platforms, setPlatforms] = useState<string[]>([])
  const [deadline, setDeadline] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const togglePlatform = (id: string) =>
    setPlatforms(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id])

  const handleSubmit = async () => {
    if (!description.trim()) { setError('Please describe your directive.'); return }
    setLoading(true); setError('')
    try {
      const goal = await api.goals.create({
        description: description.trim(),
        platforms: platforms.length > 0 ? platforms : undefined,
        deadline: deadline || undefined,
      })
      router.push(`/goals/${goal.id}`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to deploy directive')
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* Header */}
        <div style={{ padding: '3rem 3rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
              DIGITAL FORCE — OPERATIONS
            </div>
            <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.035em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, marginBottom: '0.625rem' }}>
              Deploy Directive
            </h1>
            <p style={{ fontSize: '0.875rem', color: '#475569' }}>
              Brief your autonomous agent fleet in plain language — they handle strategy, content, and execution
            </p>
          </motion.div>
        </div>

        <div style={{ padding: '2.5rem 3rem', maxWidth: 820 }}>

          {/* Directive brief */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
            style={{ marginBottom: '1.25rem', padding: '1.75rem', borderRadius: '1rem', background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1rem' }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(0,163,255,0.1)', border: '1px solid rgba(0,163,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Target size={17} style={{ color: '#33BAFF' }} />
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#E2E8F0' }}>Directive Brief</div>
                <div style={{ fontSize: '0.68rem', color: '#334155', fontWeight: 600, letterSpacing: '0.05em' }}>PLAIN LANGUAGE INSTRUCTION</div>
              </div>
            </div>
            <textarea
              className="df-textarea"
              style={{ width: '100%', minHeight: 140, marginBottom: '1.25rem', fontFamily: 'inherit', boxSizing: 'border-box' }}
              placeholder="e.g. Schedule 50 Facebook posts of our summit flyers this week, grow our LinkedIn following from 1,000 to 5,000 in 30 days, or run a multi-platform video campaign..."
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
            <div>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#334155', letterSpacing: '0.08em', marginBottom: '0.625rem' }}>EXAMPLE DIRECTIVES</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {EXAMPLES.map((ex, i) => (
                  <button key={i} onClick={() => setDescription(ex)}
                    style={{
                      textAlign: 'left', padding: '0.625rem 0.875rem', borderRadius: 8, fontSize: '0.78rem',
                      color: '#475569', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)',
                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = '#33BAFF'; e.currentTarget.style.borderColor = 'rgba(0,163,255,0.2)'; e.currentTarget.style.background = 'rgba(0,163,255,0.04)' }}
                    onMouseLeave={e => { e.currentTarget.style.color = '#475569'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.04)'; e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}>
                    <ChevronRight size={12} style={{ flexShrink: 0, opacity: 0.6 }} />
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Platform selection */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            style={{ marginBottom: '1.25rem', padding: '1.5rem', borderRadius: '1rem', background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#E2E8F0', marginBottom: '0.25rem' }}>
              Target Platforms
              <span style={{ fontWeight: 500, color: '#475569', marginLeft: 8, fontSize: '0.75rem' }}>Optional — agents decide if not specified</span>
            </div>
            <div style={{ fontSize: '0.68rem', color: '#334155', fontWeight: 600, letterSpacing: '0.06em', marginBottom: '1rem' }}>SELECT ALL THAT APPLY</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {PLATFORM_OPTIONS.map(p => (
                <button key={p.id} onClick={() => togglePlatform(p.id)}
                  style={{
                    padding: '0.75rem 1rem', borderRadius: 10, fontSize: '0.82rem', fontWeight: 700,
                    cursor: 'pointer', transition: 'all 0.15s', letterSpacing: '0.02em',
                    background: platforms.includes(p.id) ? 'rgba(0,163,255,0.12)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${platforms.includes(p.id) ? 'rgba(0,163,255,0.35)' : 'rgba(255,255,255,0.06)'}`,
                    color: platforms.includes(p.id) ? '#33BAFF' : '#64748B',
                  }}>
                  {p.label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Deadline */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            style={{ marginBottom: '2rem', padding: '1.5rem', borderRadius: '1rem', background: 'linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(15,23,42,0.25) 100%)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.875rem' }}>
              <Calendar size={15} style={{ color: '#33BAFF' }} />
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#E2E8F0' }}>
                Deadline
                <span style={{ fontWeight: 500, color: '#475569', marginLeft: 8, fontSize: '0.75rem' }}>Optional</span>
              </div>
            </div>
            <input type="date" className="df-input"
              value={deadline} onChange={e => setDeadline(e.target.value)}
              min={new Date().toISOString().split('T')[0]} />
          </motion.div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{ marginBottom: '1.25rem', padding: '0.875rem 1.125rem', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#F87171', fontSize: '0.85rem', fontWeight: 600 }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} /> {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: '1.5rem' }}>
            <button onClick={handleSubmit} disabled={loading || !description.trim()}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '0.9rem 2.5rem',
                borderRadius: '0.875rem', background: loading || !description.trim()
                  ? 'rgba(255,255,255,0.05)' : 'linear-gradient(135deg, #00A3FF, #006199)',
                border: `1px solid ${loading || !description.trim() ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.15)'}`,
                color: loading || !description.trim() ? '#334155' : '#fff',
                fontSize: '0.95rem', fontWeight: 800, cursor: loading || !description.trim() ? 'not-allowed' : 'pointer',
                boxShadow: loading || !description.trim() ? 'none' : '0 8px 32px rgba(0,163,255,0.35)',
                transition: 'all 0.2s', letterSpacing: '0.02em',
              }}>
              {loading
                ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                : <Send size={18} />}
              {loading ? 'Deploying Agents...' : 'Deploy Directive'}
            </button>
            {!loading && (
              <div style={{ fontSize: '0.78rem', color: '#334155', fontWeight: 600, letterSpacing: '0.04em' }}>
                ENTER ↵ or click to transmit
              </div>
            )}
          </motion.div>

          {/* Thinking state */}
          <AnimatePresence>
            {loading && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{ padding: '1.75rem', borderRadius: '1rem', background: 'rgba(0,163,255,0.04)', border: '1px solid rgba(0,163,255,0.12)', backdropFilter: 'blur(12px)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '1.25rem' }}>
                  <Zap size={16} style={{ color: '#33BAFF' }} />
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#33BAFF', letterSpacing: '0.04em' }}>ORCHESTRATOR SYNTHESIZING</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 5 }}>
                    <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {THINKING_STEPS.map((step, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.78rem', color: '#475569', fontWeight: 500 }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#00A3FF', flexShrink: 0, boxShadow: '0 0 6px #00A3FF' }} />
                      {step}
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: '1.25rem', fontSize: '0.72rem', color: '#334155', fontWeight: 600, letterSpacing: '0.04em' }}>
                  You will be redirected to the directive detail page when the plan is ready for authorization.
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  )
}
