import React from 'react'
import { SproutIcon, DatabaseIcon, ShieldCheckIcon } from './Icons'

export default function Header() {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand-logo">
          <div className="brand-icon-wrapper">
            <SproutIcon size={22} className="brand-icon" />
          </div>
          <div className="brand-info">
            <div className="brand-title">
              Agri<span>Intel</span> AI
            </div>
            <div className="brand-subtitle">
              Precision Agricultural Advisory & Evidence Grounding Engine
            </div>
          </div>
        </div>
      </div>

      <div className="header-right">
        <div className="header-status-pill">
          <span className="status-indicator-dot" />
          <DatabaseIcon size={14} className="status-icon" />
          <span className="status-label">ICAR RAG Infrastructure</span>
          <span className="status-badge">Online</span>
        </div>

        <div className="header-project-pill">
          <ShieldCheckIcon size={14} className="project-icon" />
          <span className="project-text">Major Project Evaluation</span>
        </div>
      </div>
    </header>
  )
}
