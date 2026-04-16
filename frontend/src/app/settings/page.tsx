'use client'

import { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import {
  Settings, Cpu, Bell, AlertTriangle, Eye, EyeOff,
  Save, CheckCircle2, AlertCircle, RefreshCw, Trash2,
  Zap, Plus, Clock, X, ToggleLeft, ToggleRight,
  Brain, Search
} from 'lucide-react'
import api from '@/lib/api'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('token') : null

type Tab = 'general' | 'integrations' | 'autonomous' | 'notifications' | 'danger'

interface FieldProps {
  label: string; id: string; value: string; placeholder?: string
  isSecret?: boolean; onChange: (v: string) => void; hint?: string
  type?: string
}

interface BriefSlot {
  id: string
  label: string
  time: string
  recurrence: 'daily' | 'weekdays' | 'weekly' | 'once'
  date?: string
}

function Field({ label, id, value, placeholder, isSecret, onChange, hint, type = 'text' }: FieldProps) {
  const [show, setShow] = useState(false)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label htmlFor={id} style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        <input
          id={id} type={isSecret && !show ? 'password' : type}
          value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          style={{
            width: '100%', padding: `0.6rem ${isSecret ? '2.75rem' : '0.875rem'} 0.6rem 0.875rem`,
            borderRadius: 10, background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.09)', color: '#fff',
            fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box',
            fontFamily: isSecret && !show ? 'monospace' : 'inherit',
          }}
        />
        {isSecret && (
          <button type="button" onClick={() => setShow(!show)}
            style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', color: 'rgba(255,255,255,0.35)', cursor: 'pointer', padding: 4 }}>
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
      {hint && <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.25)' }}>{hint}</div>}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1rem' }}>
      <div style={{ fontWeight: 600, color: '#fff', marginBottom: '1.25rem', fontSize: '0.9rem' }}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>{children}</div>
    </div>
  )
}

const RECURRENCE_OPTIONS = [
  { value: 'daily', label: 'Every day' },
  { value: 'weekdays', label: 'Weekdays only (Mon–Fri)' },
  { value: 'weekly', label: 'Weekly (Mondays)' },
  { value: 'once', label: 'One-time only' },
]

// Common IANA timezones for the picker
const POPULAR_TIMEZONES = [
  'UTC','Africa/Harare','Africa/Johannesburg','Africa/Lagos','Africa/Nairobi',
  'America/Chicago','America/Denver','America/Los_Angeles','America/New_York','America/Sao_Paulo',
  'Asia/Dubai','Asia/Kolkata','Asia/Shanghai','Asia/Singapore','Asia/Tokyo',
  'Australia/Sydney','Europe/Amsterdam','Europe/Berlin','Europe/London','Europe/Paris',
  'Pacific/Auckland',
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('general')
  const [form, setForm] = useState<Record<string, string>>({})
  const [status, setStatus] = useState<Record<string, unknown>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [showDangerConfirm, setShowDangerConfirm] = useState(false)

  // ── Autonomous mode state ──────────────────────────────────────────────────
  const [autonomousMode, setAutonomousMode]   = useState(false)
  const [timezone, setTimezone]               = useState('UTC')
  const [industry, setIndustry]               = useState('')
  const [brandVoice, setBrandVoice]           = useState('')
  const [agentTone, setAgentTone]             = useState('')
  const [briefSlots, setBriefSlots]           = useState<BriefSlot[]>([])
  const [daemonStatus, setDaemonStatus]       = useState<Record<string, unknown>>({})
  const [autonomousSaving, setAutonomousSaving] = useState(false)
  const [autonomousSaved, setAutonomousSaved]   = useState(false)

  // New brief form
  const [newSlot, setNewSlot] = useState<Omit<BriefSlot, 'id'>>({
    label: '', time: '08:00', recurrence: 'daily', date: ''
  })
  const [addingSlot, setAddingSlot] = useState(false)

  useEffect(() => {
    Promise.all([api.settings.get(), api.settings.status()])
      .then(([settings, st]) => {
        setForm(Object.fromEntries(Object.entries(settings).map(([k, v]) => [k, String(v ?? '')])))
        setStatus(st)
      })
      .catch(e => setError(e.message))

    // Load autonomous mode settings
    fetch(`${BASE}/api/agency`, { headers: authHeaders() })
      .then(r => r.json())
      .then(data => {
        setAutonomousMode(data.autonomous_mode || false)
        setTimezone(data.timezone || 'UTC')
        setIndustry(data.industry || '')
        setBrandVoice(data.brand_voice || '')
        setAgentTone(data.agent_tone || '')
        setBriefSlots(data.brief_slots || [])
      })
      .catch(() => {})

    fetch(`${BASE}/api/agency/status`, { headers: authHeaders() })
      .then(r => r.json())
      .then(setDaemonStatus)
      .catch(() => {})
  }, [])

  const authHeaders = () => {
    const token = getToken()
    return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  }

  const set = (key: string) => (val: string) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      const payload: Record<string, unknown> = {}
      const saveable = ['groq_api_key_1','groq_api_key_2','groq_api_key_3',
        'buffer_access_token','facebook_page_id','facebook_access_token',
        'qdrant_url','qdrant_api_key','smtp_host','smtp_port','smtp_username',
        'smtp_password','smtp_from_name','smtp_from_email','frontend_url',
        'cors_origins','agent_max_iterations','agent_timeout_seconds']
      for (const key of saveable) {
        if (form[key] !== undefined && !form[key].includes('•')) payload[key] = form[key]
      }
      await api.settings.update(payload)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      const st = await api.settings.status()
      setStatus(st)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally { setSaving(false) }
  }

  const handleSaveAutonomous = async () => {
    setAutonomousSaving(true)
    try {
      await fetch(`${BASE}/api/agency`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({
          autonomous_mode: autonomousMode,
          timezone, industry, brand_voice: brandVoice,
          agent_tone: agentTone,
          brief_slots: briefSlots,
        }),
      })
      setAutonomousSaved(true)
      setTimeout(() => setAutonomousSaved(false), 3000)
    } catch (e) {
      setError('Failed to save Autonomous Mode settings')
    } finally { setAutonomousSaving(false) }
  }

  const handleAddSlot = async () => {
    if (!newSlot.label || !newSlot.time) return
    const slot = { ...newSlot, id: crypto.randomUUID() } as BriefSlot
    const updated = [...briefSlots, slot]
    setBriefSlots(updated)
    setNewSlot({ label: '', time: '08:00', recurrence: 'daily', date: '' })
    setAddingSlot(false)
  }

  const handleDeleteSlot = (id: string) => {
    setBriefSlots(prev => prev.filter(s => s.id !== id))
  }

  const handleTriggerResearch = async () => {
    await fetch(`${BASE}/api/agency/trigger-research`, { method: 'POST', headers: authHeaders() })
  }

  const handleResetOverrides = async () => {
    await api.settings.resetOverrides()
    setShowDangerConfirm(false)
    window.location.reload()
  }

  const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'integrations', label: 'Integrations', icon: Cpu },
    { id: 'autonomous', label: 'Autonomous Mode', icon: Zap },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'danger', label: 'Danger Zone', icon: AlertTriangle },
  ]

  const llmStatus = status.llm as Record<string, boolean> | undefined
  const pubStatus = status.publishing as Record<string, boolean> | undefined

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '2rem', overflowY: 'auto', maxWidth: 900, margin: '0 auto', width: '100%' }}>
        {/* Header */}
        <div style={{ padding: '3rem 0 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)', marginBottom: '2rem' }}>
          <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>DIGITAL FORCE — CONFIGURATION</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
            <div>
              <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.035em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, marginBottom: '0.625rem' }}>Settings</h1>
              <p style={{ fontSize: '0.875rem', color: '#475569' }}>Configure your Digital Force agency and integrations</p>
            </div>
            <div>
              {activeTab !== 'danger' && activeTab !== 'autonomous' && (
                <button onClick={handleSave} disabled={saving} className="btn-primary" id="save-settings">
                  {saving ? <RefreshCw size={15} className="animate-spin" /> :
                   saved ? <CheckCircle2 size={15} /> : <Save size={15} />}
                  {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
                </button>
              )}
              {activeTab === 'autonomous' && (
                <button onClick={handleSaveAutonomous} disabled={autonomousSaving} className="btn-primary" id="save-autonomous">
                  {autonomousSaving ? <RefreshCw size={15} className="animate-spin" /> :
                   autonomousSaved ? <CheckCircle2 size={15} /> : <Save size={15} />}
                  {autonomousSaving ? 'Saving...' : autonomousSaved ? 'Saved!' : 'Save Autonomous Settings'}
                </button>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: '1rem',
            padding: '0.75rem 1rem', borderRadius: 10,
            background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
            color: '#FCA5A5', fontSize: '0.85rem',
          }}>
            <AlertCircle size={15} /> {error}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.04)', paddingBottom: '0.75rem', flexWrap: 'wrap' }}>
          {TABS.map(tab => {
            const Icon = tab.icon
            return (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7,
                  padding: '0.5rem 1rem', borderRadius: 10, fontSize: '0.82rem',
                  fontWeight: activeTab === tab.id ? 700 : 500, cursor: 'pointer',
                  background: activeTab === tab.id
                    ? tab.id === 'danger' ? 'rgba(239,68,68,0.1)' : tab.id === 'autonomous' ? 'rgba(0,163,255,0.1)' : 'rgba(0,163,255,0.1)'
                    : 'transparent',
                  color: activeTab === tab.id
                    ? tab.id === 'danger' ? '#FCA5A5' : '#33BAFF'
                    : tab.id === 'danger' ? 'rgba(239,68,68,0.5)' : '#64748B',
                  border: `1px solid ${activeTab === tab.id
                    ? tab.id === 'danger' ? 'rgba(239,68,68,0.2)' : 'rgba(0,163,255,0.25)'
                    : 'transparent'}`,
                  transition: 'all 0.15s',
                  letterSpacing: '0.02em',
                }}>
                <Icon size={14} />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* ── General ── */}
        {activeTab === 'general' && (
          <div>
            <Section title="Application">
              <Field id="frontend_url" label="Frontend URL" value={form.frontend_url || ''} onChange={set('frontend_url')} placeholder="http://localhost:3000" />
              <Field id="cors_origins" label="CORS Origins" value={form.cors_origins || ''} onChange={set('cors_origins')} placeholder="http://localhost:3000,https://yourdomain.com" hint="Comma-separated list of allowed origins" />
            </Section>
            <Section title="Agent Configuration">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field id="agent_max_iterations" label="Max Agent Iterations" type="number"
                  value={form.agent_max_iterations || '10'} onChange={set('agent_max_iterations')}
                  hint="How many steps an agent can take per task" />
                <Field id="agent_timeout_seconds" label="Agent Timeout (seconds)" type="number"
                  value={form.agent_timeout_seconds || '300'} onChange={set('agent_timeout_seconds')}
                  hint="Max time for a single agent run" />
              </div>
            </Section>
          </div>
        )}

        {/* ── Integrations ── */}
        {activeTab === 'integrations' && (
          <div>
            <div style={{ display: 'flex', gap: 8, marginBottom: '1.25rem', flexWrap: 'wrap' }}>
              {[
                { label: 'Groq 1', ok: llmStatus?.groq_1 },
                { label: 'Groq 2', ok: llmStatus?.groq_2 },
                { label: 'Groq 3', ok: llmStatus?.groq_3 },
                { label: 'Buffer', ok: pubStatus?.buffer },
                { label: 'Facebook', ok: pubStatus?.facebook },
              ].map(({ label, ok }) => (
                <div key={label} style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '0.35rem 0.75rem',
                  borderRadius: 8, fontSize: '0.78rem', fontWeight: 500,
                  background: ok ? 'rgba(52,211,153,0.1)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${ok ? 'rgba(52,211,153,0.25)' : 'rgba(255,255,255,0.08)'}`,
                  color: ok ? '#34D399' : 'rgba(255,255,255,0.35)',
                }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: ok ? '#34D399' : 'rgba(255,255,255,0.2)' }} />
                  {label}
                </div>
              ))}
            </div>
            <Section title="AI Language Models — Groq Cascade">
              <Field id="groq_api_key_1" label="Groq API Key 1 (Primary)" value={form.groq_api_key_1 || ''} onChange={set('groq_api_key_1')} isSecret placeholder="gsk_..." hint="console.groq.com" />
              <Field id="groq_api_key_2" label="Groq API Key 2 (Fallback)" value={form.groq_api_key_2 || ''} onChange={set('groq_api_key_2')} isSecret placeholder="gsk_..." />
              <Field id="groq_api_key_3" label="Groq API Key 3 (Emergency)" value={form.groq_api_key_3 || ''} onChange={set('groq_api_key_3')} isSecret placeholder="gsk_..." />
            </Section>
            <Section title="Social Publishing Integrations">
              <Field id="buffer_access_token" label="Buffer Access Token" value={form.buffer_access_token || ''} onChange={set('buffer_access_token')} isSecret placeholder="buffer_pub_..." hint="buffer.com/developers" />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field id="facebook_page_id" label="Facebook Page ID" value={form.facebook_page_id || ''} onChange={set('facebook_page_id')} placeholder="123456789" />
                <Field id="facebook_access_token" label="Facebook Access Token" value={form.facebook_access_token || ''} onChange={set('facebook_access_token')} isSecret placeholder="EAA..." />
              </div>
            </Section>
            <Section title="Vector Database — Qdrant">
              <Field id="qdrant_url" label="Qdrant Cloud URL" value={form.qdrant_url || ''} onChange={set('qdrant_url')} placeholder="https://xxx.qdrant.io" hint="Leave empty to use local storage" />
              <Field id="qdrant_api_key" label="Qdrant API Key" value={form.qdrant_api_key || ''} onChange={set('qdrant_api_key')} isSecret placeholder="your-qdrant-api-key" />
            </Section>
          </div>
        )}

        {/* ── Autonomous Mode ── */}
        {activeTab === 'autonomous' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* Daemon Status */}
            <div className="glass-panel" style={{ padding: '1.25rem', border: '1px solid rgba(34,211,238,0.15)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ fontWeight: 600, color: '#22D3EE', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22D3EE', boxShadow: '0 0 8px #22D3EE', animation: 'pulse 2s infinite' }} />
                  Agency Daemon Status
                </div>
                <button onClick={handleTriggerResearch} id="trigger-research"
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0.35rem 0.75rem',
                    borderRadius: 8, background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.2)',
                    color: '#22D3EE', fontSize: '0.78rem', cursor: 'pointer' }}>
                  <Search size={12} /> Run Research Now
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                {[
                  { label: 'Last Run', value: daemonStatus.daemon_last_ran ? new Date(daemonStatus.daemon_last_ran as string).toLocaleTimeString() : 'Not yet' },
                  { label: 'Last Brief', value: daemonStatus.last_brief_sent ? new Date(daemonStatus.last_brief_sent as string).toLocaleTimeString() : 'Not yet' },
                  { label: 'Active Goals', value: String(daemonStatus.active_goals || 0) },
                ].map(({ label, value }) => (
                  <div key={label} style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: '0.85rem', color: '#fff', fontWeight: 600 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Toggle */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Zap size={16} color={autonomousMode ? '#22D3EE' : 'rgba(255,255,255,0.3)'} />
                    Autonomous Mode
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
                    When ON, agents run 24/7 — proactively researching, executing goals, and sending briefings without you asking.
                  </div>
                </div>
                <button id="toggle-autonomous" onClick={() => setAutonomousMode(!autonomousMode)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  {autonomousMode
                    ? <ToggleRight size={44} color="#22D3EE" />
                    : <ToggleLeft size={44} color="rgba(255,255,255,0.2)" />}
                </button>
              </div>
            </div>

            {/* Timezone */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ fontWeight: 600, color: '#fff', marginBottom: '1rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={15} /> Your Timezone
              </div>
              <select id="timezone-select" value={timezone} onChange={e => setTimezone(e.target.value)}
                style={{ width: '100%', padding: '0.6rem 0.875rem', borderRadius: 10,
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                  color: '#fff', fontSize: '0.875rem', outline: 'none', cursor: 'pointer' }}>
                {POPULAR_TIMEZONES.map(tz => (
                  <option key={tz} value={tz} style={{ background: '#1a1a2e' }}>{tz}</option>
                ))}
              </select>
              <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.25)', marginTop: 6 }}>
                Brief times are sent in this timezone. Select yours from the list.
              </div>
            </div>

            {/* Industry & Brand Voice */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ fontWeight: 600, color: '#fff', marginBottom: '1rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Brain size={15} /> Agency Intelligence Context
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>Your Industry</label>
                  <input id="industry-input" value={industry} onChange={e => setIndustry(e.target.value)}
                    placeholder="e.g. AI Technology, Real Estate, Healthcare, E-commerce..."
                    style={{ width: '100%', padding: '0.6rem 0.875rem', borderRadius: 10, marginTop: 6,
                      background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                      color: '#fff', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>Brand Voice</label>
                  <textarea id="brand-voice-input" value={brandVoice} onChange={e => setBrandVoice(e.target.value)}
                    placeholder="Describe how your brand speaks — e.g. 'Professional but approachable, bold, future-focused, speaks to C-suite executives...'"
                    rows={3}
                    style={{ width: '100%', padding: '0.6rem 0.875rem', borderRadius: 10, marginTop: 6,
                      background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                      color: '#fff', fontSize: '0.875rem', outline: 'none', resize: 'vertical',
                      boxSizing: 'border-box', fontFamily: 'inherit' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>Digital Force Character / Tone</label>
                  <textarea id="agent-tone-input" value={agentTone} onChange={e => setAgentTone(e.target.value)}
                    placeholder="How should Digital Force speak to you directly? e.g. 'Professional executive assistant, highly concise, strict project manager...'"
                    rows={2}
                    style={{ width: '100%', padding: '0.6rem 0.875rem', borderRadius: 10, marginTop: 6,
                      background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                      color: '#fff', fontSize: '0.875rem', outline: 'none', resize: 'vertical',
                      boxSizing: 'border-box', fontFamily: 'inherit' }} />
                </div>
                <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.25)' }}>
                  The agents also learn from your training documents and past conversations automatically.
                </div>
              </div>
            </div>

            {/* Brief Slots */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Clock size={15} /> Scheduled Briefings
                </div>
                <button id="add-brief-slot" onClick={() => setAddingSlot(true)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0.4rem 0.875rem',
                    borderRadius: 8, background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.25)',
                    color: '#A78BFA', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <Plus size={13} /> Add Brief
                </button>
              </div>

              {briefSlots.length === 0 && !addingSlot && (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: 'rgba(255,255,255,0.25)', fontSize: '0.85rem' }}>
                  No briefs scheduled. Add one to get regular updates from your agency.
                </div>
              )}

              {/* Existing slots */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {briefSlots.map(slot => (
                  <div key={slot.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.75rem 1rem', borderRadius: 10,
                    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#A78BFA', boxShadow: '0 0 6px #A78BFA' }} />
                      <div>
                        <div style={{ color: '#fff', fontSize: '0.875rem', fontWeight: 500 }}>{slot.label}</div>
                        <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.75rem', marginTop: 2 }}>
                          {slot.time} · {RECURRENCE_OPTIONS.find(r=>r.value===slot.recurrence)?.label}
                          {slot.recurrence === 'once' && slot.date ? ` · ${slot.date}` : ''}
                        </div>
                      </div>
                    </div>
                    <button onClick={() => handleDeleteSlot(slot.id)}
                      style={{ background: 'none', border: 'none', color: 'rgba(239,68,68,0.5)', cursor: 'pointer', padding: 4 }}>
                      <X size={15} />
                    </button>
                  </div>
                ))}
              </div>

              {/* Add new slot form */}
              {addingSlot && (
                <div style={{ marginTop: 12, padding: '1rem', borderRadius: 12, background: 'rgba(124,58,237,0.06)', border: '1px solid rgba(124,58,237,0.15)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div>
                        <label style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>Label</label>
                        <input id="new-slot-label" value={newSlot.label} onChange={e => setNewSlot(s => ({ ...s, label: e.target.value }))}
                          placeholder="e.g. Morning Brief, Board Meeting Prep"
                          style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: 8, marginTop: 4,
                            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                            color: '#fff', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box' }} />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>Time</label>
                        <input id="new-slot-time" type="time" value={newSlot.time} onChange={e => setNewSlot(s => ({ ...s, time: e.target.value }))}
                          style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: 8, marginTop: 4,
                            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                            color: '#fff', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box', colorScheme: 'dark' }} />
                      </div>
                    </div>
                    <div>
                      <label style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>Recurrence</label>
                      <select id="new-slot-recurrence" value={newSlot.recurrence}
                        onChange={e => setNewSlot(s => ({ ...s, recurrence: e.target.value as BriefSlot['recurrence'] }))}
                        style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: 8, marginTop: 4,
                          background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                          color: '#fff', fontSize: '0.85rem', outline: 'none', cursor: 'pointer' }}>
                        {RECURRENCE_OPTIONS.map(r => (
                          <option key={r.value} value={r.value} style={{ background: '#1a1a2e' }}>{r.label}</option>
                        ))}
                      </select>
                    </div>
                    {newSlot.recurrence === 'once' && (
                      <div>
                        <label style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.4)' }}>Date</label>
                        <input id="new-slot-date" type="date" value={newSlot.date || ''} onChange={e => setNewSlot(s => ({ ...s, date: e.target.value }))}
                          style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: 8, marginTop: 4,
                            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
                            color: '#fff', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box', colorScheme: 'dark' }} />
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                      <button onClick={() => setAddingSlot(false)}
                        style={{ padding: '0.5rem 1rem', borderRadius: 8, background: 'none',
                          border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.4)',
                          fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
                      <button id="confirm-add-slot" onClick={handleAddSlot}
                        disabled={!newSlot.label || !newSlot.time}
                        style={{ padding: '0.5rem 1rem', borderRadius: 8,
                          background: newSlot.label && newSlot.time ? 'linear-gradient(135deg,#7C3AED,#4F46E5)' : 'rgba(255,255,255,0.05)',
                          border: 'none', color: '#fff', fontSize: '0.8rem', cursor: newSlot.label && newSlot.time ? 'pointer' : 'not-allowed' }}>
                        Add Brief
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Notifications ── */}
        {activeTab === 'notifications' && (
          <div>
            <Section title="Email Notifications — SMTP">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field id="smtp_host" label="SMTP Host" value={form.smtp_host || ''} onChange={set('smtp_host')} placeholder="smtp.gmail.com" />
                <Field id="smtp_port" label="SMTP Port" type="number" value={form.smtp_port || '587'} onChange={set('smtp_port')} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field id="smtp_username" label="Email Address" value={form.smtp_username || ''} onChange={set('smtp_username')} placeholder="you@gmail.com" />
                <Field id="smtp_password" label="App Password" value={form.smtp_password || ''} onChange={set('smtp_password')} isSecret placeholder="••••••••••••" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field id="smtp_from_name" label="From Name" value={form.smtp_from_name || ''} onChange={set('smtp_from_name')} placeholder="Digital Force" />
                <Field id="smtp_from_email" label="From Email" value={form.smtp_from_email || ''} onChange={set('smtp_from_email')} placeholder="noreply@yourdomain.com" />
              </div>
              <div style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.3)', padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
                For Gmail: Enable 2FA, then generate an App Password at myaccount.google.com/apppasswords
              </div>
            </Section>
          </div>
        )}

        {/* ── Danger Zone ── */}
        {activeTab === 'danger' && (
          <div className="glass-panel" style={{ padding: '1.5rem', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 16 }}>
            <div style={{ fontWeight: 600, color: '#FCA5A5', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={18} /> Danger Zone
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '1rem', borderRadius: 12, background: 'rgba(239,68,68,0.05)' }}>
              <div>
                <div style={{ color: '#fff', fontWeight: 500, fontSize: '0.9rem' }}>Reset Setting Overrides</div>
                <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', marginTop: 2 }}>
                  Revert to .env defaults. API keys entered in UI will be cleared.
                </div>
              </div>
              {!showDangerConfirm ? (
                <button onClick={() => setShowDangerConfirm(true)} className="btn-danger" style={{ flexShrink: 0 }}>
                  <Trash2 size={14} /> Reset
                </button>
              ) : (
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button onClick={() => setShowDangerConfirm(false)} className="btn-ghost" style={{ fontSize: '0.8rem' }}>Cancel</button>
                  <button onClick={handleResetOverrides} className="btn-danger" style={{ fontSize: '0.8rem' }}>Yes, reset</button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
