'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Upload, Loader2, Image as ImageIcon, Video, Music, FileText, Plus } from 'lucide-react'
import api, { MediaAsset } from '@/lib/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface AssetSelectorProps {
  onSelect: (asset: MediaAsset) => void
  onClose: () => void
}

export default function AssetSelector({ onSelect, onClose }: AssetSelectorProps) {
  const [assets, setAssets] = useState<MediaAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  const loadAssets = async () => {
    try {
      const data = await api.media.list()
      setAssets(data)
    } catch (e) {
      console.error('Failed to load media assets:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAssets()
  }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const response = await api.media.upload(fd) // Assume this returns { id, ... }
      await loadAssets()
      
      // Auto-select the newly uploaded file if we just fetched it 
      // (or if response gives us the full asset data, we can just select that)
      // Since `api.media.upload` usually returns a limited object, we re-fetch and select the newest item.
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.98 }}
      transition={{ duration: 0.2 }}
      style={{
        position: 'absolute',
        bottom: '100%',
        left: 0,
        marginBottom: '1rem',
        width: 380,
        maxHeight: 400,
        background: 'rgba(15,23,42,0.95)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '1rem',
        boxShadow: '0 -10px 40px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        overflow: 'hidden'
      }}
    >
      <div style={{
        padding: '0.875rem 1.25rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(255,255,255,0.02)'
      }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#E2E8F0', letterSpacing: '0.04em' }}>
          MEDIA LIBRARY
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex' }}>
          <X size={16} />
        </button>
      </div>

      <div style={{ padding: '1rem', flex: 1, overflowY: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '0.75rem' }}>
          
          {/* Upload Button */}
          <div style={{ position: 'relative' }}>
            <input
              type="file"
              accept="image/*,video/*,audio/*"
              onChange={handleUpload}
              style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer', zIndex: 10 }}
              disabled={uploading}
            />
            <div style={{
              width: '100%',
              aspectRatio: '1',
              borderRadius: '0.6rem',
              border: '1px dashed rgba(0,163,255,0.4)',
              background: 'rgba(0,163,255,0.05)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              opacity: uploading ? 0.6 : 1,
              transition: 'background 0.2s',
            }}>
              {uploading ? (
                <Loader2 size={24} style={{ color: '#00A3FF', animation: 'spin 1s linear infinite' }} />
              ) : (
                <>
                  <Plus size={24} style={{ color: '#33BAFF' }} />
                  <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#33BAFF' }}>Upload New</span>
                </>
              )}
            </div>
          </div>

          {/* Asset Grid */}
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: 0.5 }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', color: '#fff' }} />
              <span style={{ fontSize: '0.75rem', color: '#94A3B8' }}>Loading...</span>
            </div>
          ) : (
            assets.map(asset => (
              <div
                key={asset.id}
                onClick={() => onSelect(asset)}
                style={{
                  width: '100%',
                  aspectRatio: '1',
                  borderRadius: '0.6rem',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {asset.asset_type === 'image' && asset.public_url ? (
                  <img src={`${API_BASE}${asset.public_url}`} alt={asset.filename} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : asset.asset_type === 'video' ? (
                  <Video size={24} style={{ color: '#33BAFF' }} />
                ) : asset.asset_type === 'audio' ? (
                  <Music size={24} style={{ color: '#22D3EE' }} />
                ) : (
                  <FileText size={24} style={{ color: '#94A3B8' }} />
                )}
                <div style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
                  padding: '16px 8px 6px',
                  fontSize: '0.65rem',
                  color: '#fff',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {asset.filename}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  )
}
