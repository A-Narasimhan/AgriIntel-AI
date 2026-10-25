import React from 'react'
import { BookOpenIcon, FileTextIcon } from './Icons'

export default function SourcesCard({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="card sources-card">
      <div className="card-header">
        <div className="card-title-group">
          <BookOpenIcon size={18} className="card-icon text-emerald" />
          <h3 className="card-title">Retrieved ICAR Evidence & Citations</h3>
        </div>
        <span className="badge badge-neutral">
          {sources.length} {sources.length === 1 ? 'Source Cited' : 'Sources Cited'}
        </span>
      </div>

      <div className="sources-description">
        Direct page-level provenance retrieved from authentic ICAR research publications during vector search.
      </div>

      <div className="sources-grid">
        {sources.map((src, i) => (
          <div key={i} className="source-citation-card">
            <div className="source-card-header">
              <div className="source-card-title-area">
                <FileTextIcon size={15} className="source-file-icon text-emerald" />
                <h4 className="source-doc-title">{src.title}</h4>
              </div>

              <div className="source-tags-row">
                {src.crop && (
                  <span className="source-tag source-tag-crop">
                    {src.crop.charAt(0).toUpperCase() + src.crop.slice(1)}
                  </span>
                )}
                {src.page != null && (
                  <span className="source-tag source-tag-page">
                    Page {src.page}
                  </span>
                )}
                {src.year != null && (
                  <span className="source-tag source-tag-year">
                    {src.year}
                  </span>
                )}
                {src.regional_scope && (
                  <span className="source-tag source-tag-region">
                    Scope: {src.regional_scope}
                  </span>
                )}
              </div>
            </div>

            {src.source_id && (
              <div className="source-filename-row">
                <span className="filename-label">File:</span>
                <code className="source-filename">{src.source_id}</code>
              </div>
            )}

            {src.excerpt && (
              <div className="source-excerpt-wrapper">
                <div className="excerpt-quotation-mark">&ldquo;</div>
                <blockquote className="source-excerpt-text">
                  {src.excerpt}
                </blockquote>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
