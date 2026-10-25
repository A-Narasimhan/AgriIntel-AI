import React from 'react'
import { formatInlineText } from '../utils/advisoryParser'

/**
 * Render general markdown (paragraphs, headers, bullet points) cleanly.
 */
export default function MarkdownRenderer({ content }) {
  if (!content) return null
  const paragraphs = content.split('\n\n')

  return (
    <div className="advisory-prose">
      {paragraphs.map((p, pIdx) => {
        const trimmed = p.trim()
        if (!trimmed) return null

        if (trimmed.startsWith('### ')) {
          return <h4 key={pIdx} className="advisory-h4">{formatInlineText(trimmed.replace('### ', ''))}</h4>
        }
        if (trimmed.startsWith('## ')) {
          return <h3 key={pIdx} className="advisory-h3">{formatInlineText(trimmed.replace('## ', ''))}</h3>
        }
        if (trimmed.startsWith('# ')) {
          return <h2 key={pIdx} className="advisory-h2">{formatInlineText(trimmed.replace('# ', ''))}</h2>
        }

        // Bullet or numbered list
        const lines = trimmed.split('\n')
        const isList = lines.every(l => /^[-*•]\s+/.test(l.trim()) || /^\d+\.\s+/.test(l.trim()))

        if (isList) {
          const isOrdered = /^\d+\.\s+/.test(lines[0].trim())
          if (isOrdered) {
            return (
              <ol key={pIdx} className="advisory-ol">
                {lines.map((l, lIdx) => (
                  <li key={lIdx}>{formatInlineText(l.replace(/^\d+\.\s+/, ''))}</li>
                ))}
              </ol>
            )
          }
          return (
            <ul key={pIdx} className="advisory-ul">
              {lines.map((l, lIdx) => (
                <li key={lIdx}>{formatInlineText(l.replace(/^[-*•]\s+/, ''))}</li>
              ))}
            </ul>
          )
        }

        return <p key={pIdx} className="advisory-p">{formatInlineText(trimmed)}</p>
      })}
    </div>
  )
}
