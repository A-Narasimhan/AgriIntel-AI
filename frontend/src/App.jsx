import React, { useState } from 'react'
import Header from './components/Header'
import WeatherCard from './components/WeatherCard'
import AdvisoryCard from './components/AdvisoryCard'
import SourcesCard from './components/SourcesCard'
import KnowledgeBaseStatus from './components/KnowledgeBaseStatus'
import {
  SearchIcon,
  SparklesIcon,
  RefreshCwIcon,
  MapPinIcon,
  ActivityIcon,
  AlertTriangleIcon,
  ShieldCheckIcon,
  LayersIcon,
  CheckCircleIcon,
  BookOpenIcon,
  SproutIcon
} from './components/Icons'

const API_BASE = 'http://localhost:8001'

const CROPS = [
  { value: '', label: 'Select Target Crop' },
  { value: 'rice', label: 'Rice (Paddy)' },
  { value: 'cotton', label: 'Cotton' },
  { value: 'maize', label: 'Maize (Corn)' },
  { value: 'groundnut', label: 'Groundnut (Peanut)' },
  { value: 'soybean', label: 'Soybean' },
]

const QUICK_PRESETS = [
  {
    crop: 'rice',
    label: 'Rice: Blast Disease Control',
    query: 'How to control blast disease in paddy fields?',
    location: 'Warangal',
    stage: 'tillering',
  },
  {
    crop: 'cotton',
    label: 'Cotton: Dry Spell Irrigation',
    query: 'What is the recommended irrigation schedule during dry spells?',
    location: 'Warangal',
    stage: 'flowering',
  },
  {
    crop: 'groundnut',
    label: 'Groundnut: Tikka & Water Mgmt',
    query: 'What are the recommended practices for Tikka disease and water management in groundnut?',
    location: 'Guntur',
    stage: 'pegging',
  },
  {
    crop: 'maize',
    label: 'Maize: Fall Armyworm & NPK',
    query: 'How to control Fall Armyworm and apply fertilizers in maize crop?',
    location: 'Warangal',
    stage: 'vegetative',
  },
  {
    crop: 'soybean',
    label: 'Soybean: Yellow Mosaic & Weeds',
    query: 'How to manage yellow mosaic virus and weed control in soybean?',
    location: 'Indore',
    stage: 'vegetative',
  },
]

const STAGE_SUGGESTIONS = [
  'Seedling / Nursery',
  'Vegetative',
  'Flowering',
  'Boll / Pod Formation',
  'Maturity / Harvest',
]

export default function App() {
  const [crop, setCrop] = useState('')
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [cropStage, setCropStage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const handleApplyPreset = (preset) => {
    setCrop(preset.crop)
    setQuery(preset.query)
    setLocation(preset.location)
    setCropStage(preset.stage)
    setError(null)
  }

  const handleSubmit = async (e) => {
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
        setError(data.detail || `Server error: HTTP ${res.status}`)
      } else {
        setResult(data)
      }
    } catch (err) {
      setError(
        `Unable to reach backend API at ${API_BASE} (${err.message || 'Network Error'}). Verify that the FastAPI service is running.`
      )
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setQuery('')
    setLocation('')
    setCrop('')
    setCropStage('')
    setResult(null)
    setError(null)
  }

  return (
    <div className="app-container">
      <Header />

      <main className="app-main">
        {/* Left Column: Query Panel & System Overview */}
        <div className="sidebar-column">
          <div className="card query-form-card">
            <div className="card-header">
              <div className="card-title-group">
                <SearchIcon size={18} className="card-icon text-emerald" />
                <h2 className="card-title">Agronomic Query Parameters</h2>
              </div>
            </div>

            {/* Quick Demonstration Presets */}
            <div className="presets-section">
              <span className="presets-label">Evaluation Presets:</span>
              <div className="presets-scroll">
                {QUICK_PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`preset-chip ${crop === p.crop && query === p.query ? 'preset-chip-active' : ''}`}
                    onClick={() => handleApplyPreset(p)}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleSubmit} id="advisory-form" className="query-form">
              {/* Target Crop */}
              <div className="form-group">
                <label htmlFor="crop-select" className="form-label">
                  Target Crop <span className="label-required">*</span>
                </label>
                <div className="select-wrapper">
                  <select
                    id="crop-select"
                    className="form-control select-control"
                    value={crop}
                    onChange={e => setCrop(e.target.value)}
                  >
                    {CROPS.map(c => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Farmer Query */}
              <div className="form-group">
                <div className="form-label-row">
                  <label htmlFor="query-input" className="form-label">
                    Farmer Query <span className="label-required">*</span>
                  </label>
                  <span className="char-count">{query.length} characters</span>
                </div>
                <textarea
                  id="query-input"
                  className="form-control textarea-control"
                  placeholder="Enter farmer observation or agronomic question (e.g. How to manage blast disease, nutrient schedule, and irrigation in rice?)"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  rows={4}
                  required
                />
              </div>

              {/* Location Field */}
              <div className="form-group">
                <label htmlFor="location-input" className="form-label">
                  Location (District / Town)
                </label>
                <div className="input-with-icon">
                  <MapPinIcon size={16} className="input-icon text-muted" />
                  <input
                    id="location-input"
                    type="text"
                    className="form-control input-control"
                    placeholder="e.g. Warangal, Guntur, Nagpur, Indore"
                    value={location}
                    onChange={e => setLocation(e.target.value)}
                  />
                </div>
                <span className="field-hint">Used for live Open-Meteo precipitation & temperature intelligence.</span>
              </div>

              {/* Growth Stage Field */}
              <div className="form-group">
                <label htmlFor="stage-input" className="form-label">
                  Observed Growth Stage (Optional)
                </label>
                <div className="input-with-icon">
                  <ActivityIcon size={16} className="input-icon text-muted" />
                  <input
                    id="stage-input"
                    type="text"
                    className="form-control input-control"
                    placeholder="e.g. tillering, flowering, vegetative"
                    value={cropStage}
                    onChange={e => setCropStage(e.target.value)}
                  />
                </div>
                <div className="stage-suggestions">
                  {STAGE_SUGGESTIONS.map(st => (
                    <button
                      key={st}
                      type="button"
                      className="stage-chip"
                      onClick={() => setCropStage(st.toLowerCase())}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  id="submit-advisory-btn"
                  disabled={loading || !query.trim()}
                >
                  {loading ? (
                    <>
                      <div className="spinner" />
                      <span>Generating Agricultural Advisory...</span>
                    </>
                  ) : (
                    <>
                      <SparklesIcon size={16} />
                      <span>Generate Grounded Advisory</span>
                    </>
                  )}
                </button>

                {(query || crop || location || cropStage || result) && (
                  <button
                    type="button"
                    onClick={handleReset}
                    className="btn btn-secondary"
                  >
                    <RefreshCwIcon size={14} />
                    <span>Reset Parameters</span>
                  </button>
                )}
              </div>
            </form>
          </div>

          <KnowledgeBaseStatus />
        </div>

        {/* Right Column: Advisory & Context Results */}
        <div className="content-column">
          {/* Empty Initial State */}
          {!result && !error && !loading && (
            <div className="card empty-state-card">
              <div className="empty-state-inner">
                <div className="empty-state-icon-wrapper">
                  <SproutIcon size={36} className="text-emerald" />
                </div>
                <h3 className="empty-state-title">Agricultural Advisory Engine Ready</h3>
                <p className="empty-state-description">
                  Select a crop, input a farmer query, and specify an optional location. AgriIntel AI synthesizes grounded agronomic recommendations strictly citing peer-reviewed ICAR extension publications and live meteorological conditions.
                </p>

                <div className="empty-capabilities-grid">
                  <div className="capability-item">
                    <ShieldCheckIcon size={18} className="text-emerald" />
                    <div className="cap-info">
                      <div className="cap-title">Hallucination Controlled</div>
                      <div className="cap-desc">Refuses ungrounded chemical dosage without authentic evidence.</div>
                    </div>
                  </div>

                  <div className="capability-item">
                    <BookOpenIcon size={18} className="text-emerald" />
                    <div className="cap-info">
                      <div className="cap-title">Page-Level Provenance</div>
                      <div className="cap-desc">Every recommendation traces back to exact publication pages.</div>
                    </div>
                  </div>

                  <div className="capability-item">
                    <LayersIcon size={18} className="text-emerald" />
                    <div className="cap-info">
                      <div className="cap-title">Live Weather Grounding</div>
                      <div className="cap-desc">Precipitation & wind alerts adjust pesticide spraying advisories.</div>
                    </div>
                  </div>
                </div>

                <div className="empty-demo-prompt">
                  <span>Tip: Select any evaluation preset above to run an instant verification query.</span>
                </div>
              </div>
            </div>
          )}

          {/* Loading Skeleton State */}
          {loading && (
            <div className="card loading-card">
              <div className="loading-content">
                <div className="loading-spinner-large" />
                <h3 className="loading-title">Generating Agricultural Advisory...</h3>
                <p className="loading-subtitle">
                  Searching 1,205 ICAR chunks · Retrieving Open-Meteo forecasts · Enforcing grounding rules
                </p>
                <div className="loading-steps">
                  <div className="loading-step active">
                    <CheckCircleIcon size={14} className="text-emerald" />
                    <span>Query Understanding & Crop Resolution</span>
                  </div>
                  <div className="loading-step active">
                    <div className="step-spinner" />
                    <span>Dense Vector Retrieval (all-MiniLM-L6-v2)</span>
                  </div>
                  <div className="loading-step pending">
                    <span className="step-circle" />
                    <span>Evidence-Grounded Synthesis & Provenance Check</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="card error-card">
              <div className="error-card-header">
                <AlertTriangleIcon size={20} className="text-rose" />
                <h3 className="error-title">Advisory Generation Error</h3>
              </div>
              <p className="error-detail">{error}</p>
              <div className="error-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleSubmit}
                >
                  <RefreshCwIcon size={13} />
                  <span>Retry Request</span>
                </button>
              </div>
            </div>
          )}

          {/* Active Result View */}
          {result && !loading && (
            <div className="results-wrapper">
              <WeatherCard weather={result.weather} />
              <AdvisoryCard data={result} />
              <SourcesCard sources={result.sources} />
            </div>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <div className="footer-left">
          <span>AgriIntel AI · Smart Agricultural Advisory & Dataset Generation</span>
          <span className="footer-separator">|</span>
          <span>B.Tech Final Year Major Project Evaluation</span>
        </div>
        <div className="footer-right">
          <span>ICAR RAG Grounded</span>
          <span className="footer-separator">·</span>
          <span>Open-Meteo Intelligence</span>
        </div>
      </footer>
    </div>
  )
}
