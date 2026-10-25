import React from 'react'
import { DatabaseIcon, LayersIcon, ShieldCheckIcon, CheckCircleIcon } from './Icons'

const CROPS_META = [
  { name: 'Rice', institute: 'ICAR National Advisory', chunks: '313 chunks' },
  { name: 'Cotton', institute: 'ICAR & CICR Technical', chunks: '164 chunks' },
  { name: 'Maize', institute: 'ICAR National Advisory', chunks: '261 chunks' },
  { name: 'Groundnut', institute: 'ICAR & DGR Bulletins', chunks: '360 chunks' },
  { name: 'Soybean', institute: 'ICAR National Advisory', chunks: '107 chunks' },
]

export default function KnowledgeBaseStatus() {
  return (
    <div className="card kb-status-card">
      <div className="card-header">
        <div className="card-title-group">
          <DatabaseIcon size={16} className="card-icon text-emerald" />
          <h3 className="card-title">Curated Knowledge Base</h3>
        </div>
        <span className="badge badge-emerald">1,205 Chunks</span>
      </div>

      <div className="kb-description">
        Authentic Indian Council of Agricultural Research (ICAR) publications indexed with strict page-level citation mapping.
      </div>

      <div className="kb-crops-list">
        {CROPS_META.map(crop => (
          <div key={crop.name} className="kb-crop-row">
            <div className="kb-crop-info">
              <CheckCircleIcon size={14} className="kb-check-icon text-emerald" />
              <span className="kb-crop-name">{crop.name}</span>
              <span className="kb-crop-institute">{crop.institute}</span>
            </div>
            <span className="kb-crop-chunks">{crop.chunks}</span>
          </div>
        ))}
      </div>

      <div className="kb-tech-footer">
        <div className="kb-tech-item">
          <LayersIcon size={12} className="text-muted" />
          <span>all-MiniLM-L6-v2 (384-dim)</span>
        </div>
        <div className="kb-tech-item">
          <ShieldCheckIcon size={12} className="text-muted" />
          <span>Page Boundary Preserved</span>
        </div>
      </div>
    </div>
  )
}
