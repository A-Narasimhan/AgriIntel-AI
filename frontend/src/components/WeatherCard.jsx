import React from 'react'
import {
  ThermometerIcon,
  DropletIcon,
  CloudRainIcon,
  WindIcon,
  MapPinIcon,
  CalendarIcon,
  InfoIcon,
  SunIcon
} from './Icons'

export default function WeatherCard({ weather }) {
  if (!weather) return null

  if (!weather.is_available) {
    return (
      <div className="card weather-card">
        <div className="card-header">
          <div className="card-title-group">
            <MapPinIcon size={16} className="card-icon text-muted" />
            <h3 className="card-title">Real-Time Meteorological Context</h3>
          </div>
          <span className="badge badge-neutral">Offline Fallback</span>
        </div>
        <div className="weather-fallback-box">
          <InfoIcon size={16} className="fallback-icon" />
          <p className="fallback-text">
            {weather.note || 'No location provided. Advisory proceeds strictly using static ICAR domain evidence.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card weather-card">
      <div className="card-header">
        <div className="card-title-group">
          <MapPinIcon size={16} className="card-icon text-emerald" />
          <h3 className="card-title">Meteorological Context — {weather.location}</h3>
        </div>
        <div className="badge badge-emerald">
          <span className="status-indicator-dot dot-live" />
          <span>Open-Meteo Live</span>
        </div>
      </div>

      <div className="weather-metrics-grid">
        {weather.temperature != null && (
          <div className="metric-tile">
            <div className="metric-header">
              <ThermometerIcon size={15} className="metric-icon text-emerald" />
              <span className="metric-label">Temperature</span>
            </div>
            <div className="metric-value">
              {weather.temperature}
              <span className="metric-unit">°C</span>
            </div>
          </div>
        )}

        {weather.humidity != null && (
          <div className="metric-tile">
            <div className="metric-header">
              <DropletIcon size={15} className="metric-icon text-blue" />
              <span className="metric-label">Humidity</span>
            </div>
            <div className="metric-value">
              {weather.humidity}
              <span className="metric-unit">%</span>
            </div>
          </div>
        )}

        {weather.precipitation != null && (
          <div className="metric-tile">
            <div className="metric-header">
              <CloudRainIcon size={15} className="metric-icon text-blue" />
              <span className="metric-label">Precipitation</span>
            </div>
            <div className="metric-value">
              {weather.precipitation}
              <span className="metric-unit">mm</span>
            </div>
          </div>
        )}

        {weather.wind_speed != null && (
          <div className="metric-tile">
            <div className="metric-header">
              <WindIcon size={15} className="metric-icon text-muted" />
              <span className="metric-label">Wind Velocity</span>
            </div>
            <div className="metric-value">
              {weather.wind_speed}
              <span className="metric-unit">km/h</span>
            </div>
          </div>
        )}
      </div>

      <div className="weather-footer">
        {weather.condition && (
          <div className="weather-condition-pill">
            <SunIcon size={14} className="condition-icon text-amber" />
            <span>Condition: {weather.condition}</span>
          </div>
        )}

        {weather.forecast_summary && (
          <div className="weather-forecast-callout">
            <CalendarIcon size={15} className="forecast-icon text-emerald" />
            <span className="forecast-text">{weather.forecast_summary}</span>
          </div>
        )}
      </div>
    </div>
  )
}
