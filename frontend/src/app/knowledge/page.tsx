'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '@/components/Sidebar'
import {
  Upload, Trash2, Image as ImageIcon, Video, Music, FileText,
  Loader2, Filter, Network, CheckCircle2, AlertCircle, Plus,
  Link as LinkIcon, Edit3, Check, X, Search, RefreshCw
} from 'lucide-react'
import api, { MediaAsset, TrainingDoc } from '@/lib/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ── Tab type ────────────────────────────────────────────────
type KnowledgeTab = 'all' | 'media' | 'documents'

// ── Unified item type ────────────────────────────────────────
type UnifiedItem =
  | { kind: 'media'; data: MediaAsset }
  | { kind: 'doc'; data: TrainingDoc }

// ── Helpers ─────────────────────────────────────────────────
function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

const CATEGORIES = [
  { id: 'brand_voice',      label: 'Brand Voice' },
  { id: 'product_info',     label: 'Product / Service' },
  { id: 'market_research',  label: 'Market Research' },
  { id: 'content_examples', label: 'Content Examples' },
  { id: 'competitor',       label: 'Competitor Intel' },
  { id: 'other',            label: 'General' },
]

const STATUS_COLORS: Record<string, { color: string; bg: string }> = {
  indexed:    { color: '#34D399', bg: 'rgba(16,185,129,0.1)' },
  processing: { color: '#33BAFF', bg: 'rgba(0,163,255,0.1)' },
  failed:     { color: '#F87171', bg: 'rgba(239,68,68,0.1)' },
  pending:    { color: '#94A3B8', bg: 'rgba(148,163,184,0.1)' },
}

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.05 } } },
  item: { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.4,0,0.2,1] } } },
}

// ── Inline Rename Component ──────────────────────────────────
function InlineRename({ defaultName, onSave }: { defaultName: string; onSave: (name: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(defaultName)

  const commit = () => { onSave(value.trim() || defaultName); setEditing(false) }
  const cancel = () => { setValue(defaultName); setEditing(false) }

  if (editing) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
      <input
        autoFocus value={value} onChange={e => setValue(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') cancel() }}
        style={{
          flex: 1, background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.4)',
          borderRadius: 6, padding: '3px 8px', color: '#F8FAFC', fontSize: '0.85rem', outline: 'none', minWidth: 0,
        }}
      />
      <button onClick={commit} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#00A3FF', padding: 2 }}><Check size={14} /></button>
      <button onClick={cancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: 2 }}><X size={14} /></button>
    </div>
  )

  return (
    <button
      onClick={() => setEditing(true)}
      style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', cursor: 'pointer', padding: 0, maxWidth: '100%', textAlign: 'left' }}
    >
      <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#E2E8F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>
      <Edit3 size={12} style={{ color: '#334155', flexShrink: 0, opacity: 0.6 }} />
    </button>
  )
}

// ── Upload Ingestion Panel ───────────────────────────────────
function IngestionPanel({ onRefresh }: { onRefresh: () => void }) {
  const [tab, setTab] = useState<'file' | 'url' | 'text'>('file')
  const [category, setCategory] = useState('brand_voice')
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [rawText, setRawText] = useState('')
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState('')

  const showSuccess = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(''), 4000) }

  const handleFile = async (file: File) => {
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file); fd.append('category', category); fd.append('title', title || file.name)
    try { await api.training.upload(fd); showSuccess(`"${file.name}" indexed successfully`); onRefresh() }
    catch (e) { console.error(e) } finally { setUploading(false) }
  }

  const handleMedia = async (file: File) => {
    setUploading(true)
    const fd = new FormData(); fd.append('file', file)
    try { await api.media.upload(fd); showSuccess(`Media "${file.name}" uploaded`); onRefresh() }
    catch (e) { console.error(e) } finally { setUploading(false) }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (!file) return
    const isMedia = file.type.startsWith('image/') || file.type.startsWith('video/') || file.type.startsWith('audio/')
    isMedia ? handleMedia(file) : handleFile(file)
  }, [category, title])

  const handleUrlIngest = async () => {
    if (!url.trim()) return
    setUploading(true)
    try { await api.training.uploadUrl(url.trim(), category); showSuccess('URL ingested and indexed'); setUrl(''); onRefresh() }
    catch (e) { console.error(e) } finally { setUploading(false) }
  }

  const handleTextIngest = async () => {
    if (!rawText.trim()) return
    setUploading(true)
    const fd = new FormData()
    fd.append('raw_text', rawText.trim()); fd.append('category', category); fd.append('title', title || 'Note')
    try { await api.training.upload(fd); showSuccess('Note indexed to Knowledge Core'); setRawText(''); setTitle(''); onRefresh() }
    catch (e) { console.error(e) } finally { setUploading(false) }
  }

  const TABS = [
    { id: 'file' as const, label: 'File Drop', icon: Upload },
    { id: 'url' as const, label: 'Ingest URL', icon: LinkIcon },
    { id: 'text' as const, label: 'Note', icon: FileText },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Category selector */}
      <div style={{ padding: '1.25rem', borderRadius: '1rem', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#475569', letterSpacing: '0.08em', marginBottom: '0.875rem' }}>KNOWLEDGE CATEGORY</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          {CATEGORIES.map(c => (
            <button key={c.id} onClick={() => setCategory(c.id)}
              style={{
                width: '100%', textAlign: 'left', padding: '0.625rem 0.875rem', borderRadius: 8, fontSize: '0.82rem',
                fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                background: category === c.id ? 'rgba(0,163,255,0.12)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${category === c.id ? 'rgba(0,163,255,0.35)' : 'rgba(255,255,255,0.04)'}`,
                color: category === c.id ? '#33BAFF' : '#94A3B8',
              }}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ingestion type tabs */}
      <div style={{ padding: '1.25rem', borderRadius: '1rem', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.04)', backdropFilter: 'blur(12px)' }}>
        <div style={{ display: 'flex', gap: 4, marginBottom: '1rem', padding: 4, borderRadius: 10, background: 'rgba(255,255,255,0.03)' }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                flex: 1, padding: '0.45rem 0.5rem', borderRadius: 7, fontSize: '0.75rem', fontWeight: 600,
                cursor: 'pointer', transition: 'all 0.15s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                background: tab === t.id ? 'rgba(0,163,255,0.15)' : 'transparent',
                color: tab === t.id ? '#33BAFF' : '#64748B',
                border: `1px solid ${tab === t.id ? 'rgba(0,163,255,0.3)' : 'transparent'}`,
              }}>
              <t.icon size={12} /> {t.label}
            </button>
          ))}
        </div>

        {/* Optional title */}
        {(tab === 'text') && (
          <input className="df-input" style={{ marginBottom: '0.75rem' }}
            placeholder="Note title..." value={title} onChange={e => setTitle(e.target.value)} />
        )}

        {tab === 'file' && (
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('knowledge-file-input')?.click()}
            style={{
              border: `2px dashed ${dragging ? 'rgba(0,163,255,0.6)' : 'rgba(255,255,255,0.08)'}`,
              borderRadius: '0.875rem', padding: '2.5rem 1rem', textAlign: 'center', cursor: 'pointer',
              background: dragging ? 'rgba(0,163,255,0.05)' : 'transparent', transition: 'all 0.2s',
            }}>
            <input id="knowledge-file-input" type="file" style={{ display: 'none' }}
              accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.mp4,.mov,.csv,.xlsx,.mp3,.wav,.gif,.webp"
              onChange={e => {
                const file = e.target.files?.[0]; if (!file) return
                const isMedia = file.type.startsWith('image/') || file.type.startsWith('video/') || file.type.startsWith('audio/')
                isMedia ? handleMedia(file) : handleFile(file)
              }} />
            {uploading
              ? <Loader2 size={28} style={{ color: '#00A3FF', margin: '0 auto 0.75rem', animation: 'spin 1s linear infinite' }} />
              : <Upload size={28} style={{ color: '#334155', margin: '0 auto 0.75rem' }} />}
            <div style={{ fontSize: '0.82rem', color: '#64748B', fontWeight: 600 }}>Drop or click to inject</div>
            <div style={{ fontSize: '0.72rem', color: '#334155', marginTop: 4 }}>PDF, DOCX, TXT, Images, Video, Audio</div>
          </div>
        )}

        {tab === 'url' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <input className="df-input" placeholder="https://article-or-page-to-scrape.com" value={url} onChange={e => setUrl(e.target.value)} />
            <button onClick={handleUrlIngest} disabled={uploading || !url.trim()}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '0.75rem', borderRadius: 10, background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '0.85rem', fontWeight: 700, cursor: uploading || !url.trim() ? 'not-allowed' : 'pointer', opacity: uploading || !url.trim() ? 0.6 : 1 }}>
              {uploading ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={15} />}
              Ingest URL
            </button>
          </div>
        )}

        {tab === 'text' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <textarea className="df-textarea" placeholder="Paste brand guidelines, product notes, key messaging..." value={rawText} onChange={e => setRawText(e.target.value)} />
            <button onClick={handleTextIngest} disabled={uploading || !rawText.trim()}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '0.75rem', borderRadius: 10, background: 'linear-gradient(135deg, #00A3FF, #006199)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: '0.85rem', fontWeight: 700, cursor: uploading || !rawText.trim() ? 'not-allowed' : 'pointer', opacity: uploading || !rawText.trim() ? 0.6 : 1 }}>
              {uploading ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={15} />}
              Commit to Core
            </button>
          </div>
        )}

        {/* Success flash */}
        <AnimatePresence>
          {success && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: 8, padding: '0.625rem 0.875rem', borderRadius: 8, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', color: '#34D399', fontSize: '0.8rem', fontWeight: 600 }}>
              <CheckCircle2 size={14} /> {success}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ── Main Knowledge Core Page ─────────────────────────────────
export default function KnowledgePage() {
  const [mediaItems, setMediaItems] = useState<MediaAsset[]>([])
  const [docItems, setDocItems] = useState<TrainingDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<KnowledgeTab>('all')
  const [search, setSearch] = useState('')
  const [selectedMedia, setSelectedMedia] = useState<MediaAsset | null>(null)

  const loadAll = async () => {
    setLoading(true)
    try {
      const [media, docs] = await Promise.all([api.media.list(), api.training.list()])
      setMediaItems(media)
      setDocItems(docs)
    } finally { setLoading(false) }
  }

  useEffect(() => { loadAll() }, [])

  const handleDeleteMedia = async (id: string) => {
    await api.media.delete(id)
    setMediaItems(prev => prev.filter(a => a.id !== id))
    if (selectedMedia?.id === id) setSelectedMedia(null)
  }

  const handleDeleteDoc = async (id: string) => {
    await api.training.delete(id)
    setDocItems(prev => prev.filter(d => d.id !== id))
  }

  // Combine and filter
  const allItems: UnifiedItem[] = [
    ...(tab === 'all' || tab === 'media' ? mediaItems.map(d => ({ kind: 'media' as const, data: d })) : []),
    ...(tab === 'all' || tab === 'documents' ? docItems.map(d => ({ kind: 'doc' as const, data: d })) : []),
  ]
  const filtered = search
    ? allItems.filter(item => (item.kind === 'media' ? item.data.filename : item.data.title).toLowerCase().includes(search.toLowerCase()))
    : allItems

  const TABS = [
    { id: 'all' as const, label: 'All', count: mediaItems.length + docItems.length },
    { id: 'media' as const, label: 'Media', count: mediaItems.length },
    { id: 'documents' as const, label: 'Documents', count: docItems.length },
  ]

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto" style={{ background: '#080B12' }}>

        {/* ── Header ── */}
        <div style={{ padding: '3rem 3rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '0.75rem' }}>
              DIGITAL FORCE — INTELLIGENCE
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
              <div>
                <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '-0.035em', background: 'linear-gradient(180deg, #FFFFFF 0%, #94A3B8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', lineHeight: 1.1, marginBottom: '0.625rem' }}>
                  Knowledge Core
                </h1>
                <p style={{ fontSize: '0.875rem', color: '#475569' }}>
                  The central intelligence hub — all assets accessible by agents via semantic search
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0.4rem 0.875rem', borderRadius: 8, background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.2)' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00A3FF', boxShadow: '0 0 8px #00A3FF' }} />
                  <span style={{ fontSize: '0.72rem', color: '#33BAFF', fontWeight: 700, letterSpacing: '0.05em' }}>SEMANTIC SEARCH ACTIVE</span>
                </div>
                <button onClick={loadAll} style={{ padding: '0.5rem', borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', cursor: 'pointer', color: '#64748B', display: 'flex', transition: 'color 0.2s' }}
                  onMouseEnter={e => (e.currentTarget.style.color = '#94A3B8')}
                  onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}>
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>
          </motion.div>
        </div>

        <div style={{ padding: '2rem 3rem', display: 'grid', gridTemplateColumns: '1fr 280px', gap: '2rem', alignItems: 'start' }}>

          {/* ── Left: Items Grid ── */}
          <div>
            {/* Search + Tabs */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', alignItems: 'center' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#475569' }} />
                <input style={{ width: '100%', padding: '0.65rem 1rem 0.65rem 2.25rem', borderRadius: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)', color: '#F8FAFC', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box' }}
                  placeholder="Search knowledge..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
              <div style={{ display: 'flex', gap: 4, padding: 4, borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)', flexShrink: 0 }}>
                {TABS.map(t => (
                  <button key={t.id} onClick={() => setTab(t.id)}
                    style={{ padding: '0.4rem 0.875rem', borderRadius: 7, fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s', background: tab === t.id ? 'rgba(0,163,255,0.15)' : 'transparent', color: tab === t.id ? '#33BAFF' : '#64748B', border: `1px solid ${tab === t.id ? 'rgba(0,163,255,0.3)' : 'transparent'}` }}>
                    {t.label} <span style={{ opacity: 0.6 }}>({t.count})</span>
                  </button>
                ))}
              </div>
              <span style={{ fontSize: '0.78rem', color: '#334155', fontWeight: 600, flexShrink: 0, letterSpacing: '0.04em' }}>{filtered.length} items</span>
            </div>

            {/* Items */}
            {loading ? (
              <div style={{ padding: '5rem', display: 'flex', justifyContent: 'center', borderRadius: '1rem', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(255,255,255,0.03)' }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
                </div>
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '5rem 2rem', textAlign: 'center', borderRadius: '1rem', border: '1px dashed rgba(0,163,255,0.1)', background: 'rgba(0,163,255,0.02)' }}>
                <Network size={36} style={{ color: '#334155', margin: '0 auto 1rem' }} />
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#475569', marginBottom: 6 }}>No knowledge assets found</div>
                <div style={{ fontSize: '0.8rem', color: '#334155' }}>Inject documents, media, or notes using the panel on the right</div>
              </div>
            ) : (
              <motion.div variants={stagger.container} initial="hidden" animate="show"
                style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {filtered.map(item => (
                  <motion.div key={item.kind === 'media' ? item.data.id : item.data.id} variants={stagger.item}>
                    {item.kind === 'media' ? (
                      // ── Media Row ──
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.875rem 1.25rem',
                        borderRadius: '0.875rem', background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(255,255,255,0.04)',
                        backdropFilter: 'blur(8px)', cursor: 'pointer',
                        transition: 'border-color 0.2s', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)',
                      }}
                        onClick={() => setSelectedMedia(item.data)}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(0,163,255,0.2)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.04)')}>
                        {/* Thumbnail / Icon */}
                        <div style={{ width: 48, height: 48, borderRadius: 8, overflow: 'hidden', flexShrink: 0, background: 'rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {item.data.asset_type === 'image' && item.data.public_url
                            ? <img src={`${API_BASE}${item.data.public_url}`} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            : item.data.asset_type === 'video' ? <Video size={20} style={{ color: '#33BAFF' }} />
                            : item.data.asset_type === 'audio' ? <Music size={20} style={{ color: '#22D3EE' }} />
                            : <FileText size={20} style={{ color: '#94A3B8' }} />}
                        </div>
                        {/* Name (inline rename) */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <InlineRename defaultName={item.data.filename} onSave={name => console.log('Rename media', item.data.id, name)} />
                          <div style={{ fontSize: '0.72rem', color: '#475569', marginTop: 3 }}>
                            {item.data.asset_type?.toUpperCase() || 'UNKNOWN'} · {item.data.file_size_bytes ? formatBytes(item.data.file_size_bytes) : '0B'} · Used {item.data.usage_count || 0}×
                          </div>
                        </div>
                        {/* Status pill */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 6, background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                          <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#34D399' }} />
                          <span style={{ fontSize: '0.68rem', color: '#34D399', fontWeight: 700, letterSpacing: '0.04em' }}>MEDIA</span>
                        </div>
                        <button onClick={e => { e.stopPropagation(); handleDeleteMedia(item.data.id) }}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#334155', padding: 4, transition: 'color 0.2s' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#F87171')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#334155')}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    ) : (
                      // ── Document Row ──
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.875rem 1.25rem',
                        borderRadius: '0.875rem', background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(255,255,255,0.04)',
                        backdropFilter: 'blur(8px)',
                        transition: 'border-color 0.2s', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)',
                      }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(0,163,255,0.2)')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.04)')}>
                        {/* Icon */}
                        <div style={{ width: 48, height: 48, borderRadius: 8, flexShrink: 0, background: 'rgba(0,163,255,0.08)', border: '1px solid rgba(0,163,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {item.data.source_type === 'url' ? <LinkIcon size={20} style={{ color: '#33BAFF' }} /> : <FileText size={20} style={{ color: '#33BAFF' }} />}
                        </div>
                        {/* Name (inline rename) */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <InlineRename defaultName={item.data.title} onSave={name => console.log('Rename doc', item.data.id, name)} />
                          <div style={{ fontSize: '0.72rem', color: '#475569', marginTop: 3 }}>
                            {item.data.source_type?.toUpperCase() || 'UNKNOWN'} · {item.data.category?.replace('_', ' ')} · {item.data.chunk_count || 0} chunks
                          </div>
                        </div>
                        {/* Status */}
                        {(() => {
                          const s = STATUS_COLORS[item.data.processing_status] || STATUS_COLORS.pending
                          return (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 6, background: s.bg, border: `1px solid ${s.color}30` }}>
                              <div style={{ width: 5, height: 5, borderRadius: '50%', background: s.color }} />
                              <span style={{ fontSize: '0.68rem', color: s.color, fontWeight: 700, letterSpacing: '0.04em' }}>{item.data.processing_status.toUpperCase()}</span>
                            </div>
                          )
                        })()}
                        <button onClick={() => handleDeleteDoc(item.data.id)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#334155', padding: 4, transition: 'color 0.2s' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#F87171')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#334155')}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    )}
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>

          {/* ── Right: Ingestion Panel ── */}
          <div style={{ position: 'sticky', top: '2rem' }}>
            <IngestionPanel onRefresh={loadAll} />
          </div>
        </div>

        {/* ── Media Detail Drawer ── */}
        <AnimatePresence>
          {selectedMedia && (
            <motion.div
              initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              style={{
                position: 'fixed', right: 0, top: 0, bottom: 0, width: 320,
                background: 'rgba(8,11,18,0.95)', backdropFilter: 'blur(24px)',
                borderLeft: '1px solid rgba(255,255,255,0.05)',
                boxShadow: '-20px 0 60px rgba(0,0,0,0.5)',
                zIndex: 200, overflow: 'auto',
              }}>
              <div style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#475569', letterSpacing: '0.06em' }}>ASSET DETAIL</span>
                  <button onClick={() => setSelectedMedia(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', padding: 4, display: 'flex' }}>
                    <X size={18} />
                  </button>
                </div>

                {selectedMedia.asset_type === 'image' && (
                  <div style={{ borderRadius: 10, overflow: 'hidden', marginBottom: '1.25rem', aspectRatio: '16/9', background: 'rgba(255,255,255,0.03)' }}>
                    <img src={`${API_BASE}${selectedMedia.public_url}`} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                  </div>
                )}

                <div style={{ marginBottom: '1rem' }}>
                  <InlineRename defaultName={selectedMedia.filename} onSave={name => console.log('Renamed', selectedMedia.id, name)} />
                  <div style={{ fontSize: '0.72rem', color: '#475569', marginTop: 6 }}>
                    {selectedMedia.asset_type?.toUpperCase() || 'UNKNOWN'} · {selectedMedia.file_size_bytes ? formatBytes(selectedMedia.file_size_bytes) : '0B'} · {selectedMedia.usage_count || 0} uses
                  </div>
                </div>

                {selectedMedia.ai_description && (
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#334155', letterSpacing: '0.06em', marginBottom: 6 }}>AI ANALYSIS</div>
                    <p style={{ fontSize: '0.82rem', color: '#64748B', lineHeight: 1.6 }}>{selectedMedia.ai_description}</p>
                  </div>
                )}

                {(selectedMedia.auto_tags ?? []).length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#334155', letterSpacing: '0.06em', marginBottom: 8 }}>AUTO TAGS</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {(selectedMedia.auto_tags ?? []).map(tag => (
                        <span key={tag} style={{ padding: '3px 10px', borderRadius: 6, background: 'rgba(0,163,255,0.1)', color: '#33BAFF', fontSize: '0.72rem', fontWeight: 600 }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                )}

                <button onClick={() => handleDeleteMedia(selectedMedia.id)}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '0.75rem', borderRadius: 10, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#F87171', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}>
                  <Trash2 size={15} /> Remove Asset
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </main>
    </div>
  )
}
