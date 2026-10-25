import React from 'react'

/**
 * Format inline markdown like **bold**, *italic*, and code into React nodes.
 */
export function formatInlineText(text) {
  if (!text) return null

  // Split by bold (**text**)
  const parts = []
  const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index))
    }
    const token = match[0]
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        React.createElement('strong', { key: match.index, className: 'advisory-bold' }, token.slice(2, -2))
      )
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(
        React.createElement('em', { key: match.index, className: 'advisory-italic' }, token.slice(1, -1))
      )
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        React.createElement('code', { key: match.index, className: 'advisory-code' }, token.slice(1, -1))
      )
    }
    lastIndex = match.index + token.length
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex))
  }

  return parts.length > 0 ? parts : text
}

/**
 * Parse structured AgriIntel recommendation items:
 * "1. Text ... \n   ↳ *Citation*: [Source: Title (file.pdf), Page X]"
 */
export function parseStructuredAdvisory(rawText) {
  if (!rawText) return null

  const isUngrounded = rawText.includes('Reliable supporting information was not found') ||
    rawText.includes('No agricultural recommendation has been generated')

  if (isUngrounded) {
    return {
      type: 'ungrounded',
      message: rawText.trim(),
    }
  }

  const lines = rawText.split('\n')
  let title = ''
  let queryText = ''
  let stageText = ''
  let weatherAlert = null
  const recommendations = []
  let disclaimer = ''

  let inRecSection = false
  let currentRec = null

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue

    if (line.startsWith('### Agricultural Advisory')) {
      title = line.replace('###', '').trim()
      continue
    }

    if (line.startsWith('**Query**:')) {
      queryText = line.replace('**Query**:', '').trim()
      continue
    }

    if (line.startsWith('**Observed Crop Growth Stage**:')) {
      stageText = line.replace('**Observed Crop Growth Stage**:', '').trim()
      continue
    }

    if (line.includes('Weather Alert') || line.includes('⚠️ *Weather Alert*:')) {
      weatherAlert = line.replace(/⚠️|\*Weather Alert\*:|\*\*/g, '').trim()
      continue
    }

    if (line.startsWith('**Curated Agricultural Recommendations**:')) {
      inRecSection = true
      continue
    }

    if (line.startsWith('Recommendations below are excerpts from retrieved documents')) {
      disclaimer = line
      inRecSection = false
      if (currentRec) {
        recommendations.push(currentRec)
        currentRec = null
      }
      continue
    }

    if (inRecSection) {
      // Check for numbered item start: "1. ", "2. ", etc.
      const numMatch = line.match(/^(\d+)\.\s+(.*)/)
      if (numMatch) {
        if (currentRec) {
          recommendations.push(currentRec)
        }
        currentRec = {
          number: parseInt(numMatch[1], 10),
          text: numMatch[2],
          citation: null,
        }
        continue
      }

      // Check for citation marker: "↳ *Citation*: [Source: ...]"
      if (line.includes('Citation*') || line.includes('↳') || line.includes('[Source:')) {
        const citationRaw = line.replace(/^[\s↳*Citation:*]+/, '').trim()
        if (currentRec) {
          currentRec.citation = citationRaw.replace(/^\[|\]$/g, '')
        }
        continue
      }

      // If ongoing recommendation text
      if (currentRec) {
        currentRec.text += ' ' + line
      }
    }
  }

  if (currentRec) {
    recommendations.push(currentRec)
  }

  // If structured recommendations were parsed, return structured format
  if (recommendations.length > 0) {
    return {
      type: 'structured',
      title,
      queryText,
      stageText,
      weatherAlert,
      recommendations,
      disclaimer,
    }
  }

  // Fallback to general markdown renderer
  return {
    type: 'markdown',
    rawText,
  }
}
