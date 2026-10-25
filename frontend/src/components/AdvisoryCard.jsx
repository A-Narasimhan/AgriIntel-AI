import React, { useState } from 'react'
import {
  ShieldCheckIcon,
  AlertTriangleIcon,
  CopyIcon,
  CheckCircleIcon,
  BookOpenIcon,
  InfoIcon,
  ActivityIcon,
  SproutIcon
} from './Icons'
import { parseStructuredAdvisory, formatInlineText } from '../utils/advisoryParser'
import MarkdownRenderer from './MarkdownRenderer'

export default function AdvisoryCard({ data }) {
  const [copied, setCopied] = useState(false)

  if (!data) return null

  const parsed = parseStructuredAdvisory(data.advisory)

  const handleCopyId = () => {
    if (data.interaction_id) {
      navigator.clipboard.writeText(data.interaction_id)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Format intent label into title case
  const formatIntent = (intent) => {
    if (!intent) return 'General'
    return intent
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ')
  }

  return (
    <div className="card advisory-card">
      <div className="card-header">
        <div className="card-title-group">
          <SproutIcon size={18} className="card-icon text-emerald" />
          <h3 className="card-title">Grounded Agronomic Advisory</h3>
        </div>

        <div className="grounding-status-container">
          {data.evidence_grounded ? (
            <div className="badge badge-grounded">
              <ShieldCheckIcon size={14} className="badge-icon" />
              <span>Grounded in ICAR Evidence</span>
            </div>
          ) : (
            <div className="badge badge-ungrounded">
              <AlertTriangleIcon size={14} className="badge-icon" />
              <span>Insufficient Domain Evidence</span>
            </div>
          )}
        </div>
      </div>

      {/* Metadata Pill Row */}
      <div className="advisory-meta-bar">
        {data.crop && (
          <div className="meta-pill meta-crop">
            <span className="meta-pill-label">Crop</span>
            <span className="meta-pill-value">{data.crop.charAt(0).toUpperCase() + data.crop.slice(1)}</span>
          </div>
        )}

        {data.intent && (
          <div className="meta-pill meta-intent">
            <ActivityIcon size={13} className="meta-pill-icon" />
            <span className="meta-pill-label">Intent</span>
            <span className="meta-pill-value">{formatIntent(data.intent)}</span>
          </div>
        )}

        {data.crop_stage && (
          <div className="meta-pill meta-stage">
            <span className="meta-pill-label">Stage</span>
            <span className="meta-pill-value">{data.crop_stage}</span>
          </div>
        )}

        {data.interaction_id && (
          <button
            type="button"
            className="interaction-id-chip"
            onClick={handleCopyId}
            title="Click to copy interaction ID"
          >
            <span className="id-label">ID:</span>
            <span className="id-code">{data.interaction_id.slice(0, 8)}...</span>
            {copied ? (
              <CheckCircleIcon size={13} className="text-emerald" />
            ) : (
              <CopyIcon size={13} className="text-muted" />
            )}
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="advisory-content-area">
        {parsed?.type === 'ungrounded' && (
          <div className="ungrounded-alert-card">
            <div className="alert-header">
              <AlertTriangleIcon size={18} className="alert-icon text-amber" />
              <h4 className="alert-title">Strict Hallucination Prevention Triggered</h4>
            </div>
            <p className="alert-message">{parsed.message}</p>
            <div className="alert-footnote">
              <InfoIcon size={14} className="footnote-icon" />
              <span>
                Under AgriIntel RAG safety guidelines, the system refuses to fabricate unverified pesticide dosages or chemical formulations when authentic source documents lack coverage.
              </span>
            </div>
          </div>
        )}

        {parsed?.type === 'structured' && (
          <div className="structured-recommendations-wrapper">
            {parsed.weatherAlert && (
              <div className="weather-alert-banner">
                <AlertTriangleIcon size={16} className="text-amber" />
                <span className="weather-alert-text">
                  {formatInlineText(parsed.weatherAlert)}
                </span>
              </div>
            )}

            <div className="recommendations-list">
              <div className="section-subheading">
                <span>Domain Recommendations from Curated Publications</span>
                <span className="rec-count-badge">{parsed.recommendations.length} Steps</span>
              </div>

              {parsed.recommendations.map((rec, idx) => (
                <div key={idx} className="recommendation-item-card">
                  <div className="rec-badge-col">
                    <span className="rec-number-badge">
                      {String(rec.number || idx + 1).padStart(2, '0')}
                    </span>
                  </div>
                  <div className="rec-body-col">
                    <div className="rec-text-body">
                      {formatInlineText(rec.text)}
                    </div>

                    {rec.citation && (
                      <div className="rec-citation-tag">
                        <BookOpenIcon size={12} className="citation-icon text-emerald" />
                        <span className="citation-text">{rec.citation}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {parsed.disclaimer && (
              <div className="advisory-disclaimer-box">
                <InfoIcon size={14} className="disclaimer-icon text-muted" />
                <span className="disclaimer-text">{parsed.disclaimer}</span>
              </div>
            )}
          </div>
        )}

        {parsed?.type === 'markdown' && (
          <div className="advisory-generic-wrapper">
            <MarkdownRenderer content={parsed.rawText} />
          </div>
        )}
      </div>
    </div>
  )
}
