import { useState } from 'react'
import './index.css'

const API_BASE = 'http://localhost:8000'

const CROPS = [
  { value: '', label: '— Select Crop —' },
  { value: 'rice', label: '🌾 Rice' },
  { value: 'cotton', label: '🌿 Cotton' },
  { value: 'maize', label: '🌽 Maize' },
  { value: 'groundnut', label: '🥜 Groundnut' },
  { value: 'soybean', label: '🫘 Soybean' },
]

function WeatherCard({ weather }) {
  if (!weather) return null

  if (!weather.is_available) {
    return (
      <div className="card">
        <div className="card-title">🌦️ Weather Context</div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{weather.note}</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">🌦️ Weather — {weather.location}</div>
      <div className="weather-grid">
        {weather.temperature != null && (
          <div className="weather-stat">
            <div className="weather-stat-label">Temperature</div>
            <div className="weather-stat-value">{weather.temperature}°C</div>
          </div>
        )}
        {weather.humidity != null && (
          <div className="weather-stat">
            <div className="weather-stat-label">Humidity</div>
            <div className="weather-stat-value">{weather.humidity}%</div>
          </div>
        )}
        {weather.precipitation != null && (
          <div className="weather-stat">
            <div className="weather-stat-label">Precipitation</div>
            <div className="weather-stat-value">{weather.precipitation} mm</div>
          </div>
        )}
        {weather.wind_speed != null && (
          <div className="weather-stat">
            <div className="weather-stat-label">Wind Speed</div>
            <div className="weather-stat-value">{weather.wind_speed} km/h</div>
          </div>
        )}
      </div>
      {weather.condition && <div className="weather-condition">☁️ {weather.condition}</div>}
      {weather.forecast_summary && (
        <div className="weather-condition" style={{ marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
          📅 {weather.forecast_summary}
        </div>
      )}
    </div>
  )
}

function SourcesCard({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="card">
      <div className="card-title">📚 Agricultural Sources Cited</div>
      <div className="sources-list">
        {sources.map((src, i) => (
          <div key={i} className="source-item">
            <div className="source-title">{src.title}</div>
            <div className="source-meta">
              {src.crop && <span className="chip chip-green" style={{ marginRight: '0.4rem' }}>{src.crop}</span>}
              {src.page && <span>Page {src.page}</span>}
              {src.year && <span style={{ marginLeft: '0.5rem' }}>· {src.year}</span>}
            </div>
            {src.excerpt && (
              <div className="source-excerpt">&ldquo;{src.excerpt}&rdquo;</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AdvisoryCard({ data }) {
  if (!data) return null

  return (
    <div className="card">
      <div className="card-title">🌱 Advisory Response</div>
      <div className="meta-row">
        {data.intent && <span className="chip chip-blue">Intent: {data.intent.replace('_', ' ')}</span>}
        {data.crop && <span className="chip chip-green">{data.crop}</span>}
        {data.crop_stage && <span className="chip chip-yellow">{data.crop_stage}</span>}
        {data.evidence_grounded
          ? <span className="chip chip-green">✓ Evidence Grounded</span>
          : <span className="chip chip-red">⚠ No Evidence Found</span>
        }
      </div>
      <div className="advisory-text">{data.advisory}</div>
      {data.interaction_id && (
        <div style={{ marginTop: '0.6rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          Interaction ID: {data.interaction_id}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [crop, setCrop] = useState('')
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [cropStage, setCropStage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload = { query: query.trim() }
      if (crop) payload.crop = crop
      if (location.trim()) payload.location = location.trim()
      if (cropStage.trim()) payload.crop_stage = cropStage.trim()

      const res = await fetch(`${API_BASE}/advisory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || `Server error: ${res.status}`)
      } else {
        setResult(data)
      }
    } catch (err) {
      setError(`Connection error: ${err.message}. Make sure the backend is running at ${API_BASE}`)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setQuery('')
    setLocation('')
    setCrop('')
    setCropStage('')
    setResult(null)
    setError(null)
  }

  return (
    <div className="app-wrapper">
      <header>
        <div className="logo">
          <div className="logo-icon">🌾</div>
          <div className="logo-text">Agri<span>Intel</span> AI</div>
        </div>
        <span className="header-badge">Smart Agricultural Advisory</span>
      </header>

      <main>
        {/* LEFT: Input Panel */}
        <div>
          <form className="card" onSubmit={handleSubmit} id="advisory-form">
            <div className="card-title">🔍 Farmer Query</div>

            <div className="form-group">
              <label htmlFor="crop-select">Target Crop *</label>
              <select
                id="crop-select"
                value={crop}
                onChange={e => setCrop(e.target.value)}
              >
                {CROPS.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="query-input">Farmer Query *</label>
              <textarea
                id="query-input"
                placeholder="e.g. What are the symptoms and control measures for blast disease in paddy?"
                value={query}
                onChange={e => setQuery(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="location-input">Location</label>
              <input
                id="location-input"
                type="text"
                placeholder="e.g. Warangal, Guntur, Nagpur…"
                value={location}
                onChange={e => setLocation(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="stage-input">Crop Growth Stage (optional)</label>
              <input
                id="stage-input"
                type="text"
                placeholder="e.g. tillering, flowering, boll formation…"
                value={cropStage}
                onChange={e => setCropStage(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="btn-primary"
              id="submit-advisory-btn"
              disabled={loading || !query.trim()}
            >
              {loading
                ? <><div className="spinner" /> Generating Advisory…</>
                : '⚡ Get Agricultural Advisory'
              }
            </button>

            {result && (
              <button
                type="button"
                onClick={handleReset}
                style={{
                  width: '100%',
                  marginTop: '0.6rem',
                  padding: '0.55rem',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontFamily: "'Inter', sans-serif",
                  fontSize: '0.85rem',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={e => e.target.style.borderColor = 'var(--text-secondary)'}
                onMouseLeave={e => e.target.style.borderColor = 'var(--border)'}
              >
                ↺ New Query
              </button>
            )}
          </form>

          {/* Knowledge Base Status Info */}
          <div className="card" style={{ marginTop: '1.25rem' }}>
            <div className="card-title">ℹ️ Knowledge Base Status</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
              <p>Currently supported crops:</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                {['Rice', 'Cotton', 'Maize', 'Groundnut', 'Soybean'].map(c => (
                  <span key={c} className="chip chip-green">{c}</span>
                ))}
              </div>
              <p style={{ marginTop: '0.75rem', color: 'var(--text-muted)' }}>
                Place approved ICAR PDF documents in <code style={{ color: 'var(--accent-green)' }}>data/knowledge_base/&lt;crop&gt;/</code> and run <code style={{ color: 'var(--accent-green)' }}>build_knowledge_base.py</code> to index them.
              </p>
            </div>
          </div>
        </div>

        {/* RIGHT: Results Panel */}
        <div className="results-panel">
          {!result && !error && (
            <div className="card">
              <div className="empty-state">
                <div className="empty-icon">🌿</div>
                <div className="empty-title">Ready for Farmer Queries</div>
                <div className="empty-subtitle">
                  Enter a crop, your query, and optional location to receive a grounded agricultural advisory sourced from curated ICAR publications.
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="card">
              <div className="error-banner">
                <strong>⚠ Error:</strong> {error}
              </div>
            </div>
          )}

          {result && (
            <>
              <WeatherCard weather={result.weather} />
              <AdvisoryCard data={result} />
              <SourcesCard sources={result.sources} />
            </>
          )}
        </div>
      </main>

      <footer>
        AgriIntel AI · B.Tech Major Project · Agricultural Advisory grounded in ICAR publications
        · Powered by RAG + Open-Meteo Weather
      </footer>
    </div>
  )
}
