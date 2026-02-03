'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Alert } from '@/lib/types'
import { AlertTriangle, ArrowRight, Shield, Activity, Loader2 } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000'

function getRiskColor(score: number): string {
  if (score >= 0.8) return 'text-accent-red bg-accent-red/10 border-accent-red/30'
  if (score >= 0.6) return 'text-accent-orange bg-accent-orange/10 border-accent-orange/30'
  return 'text-accent-green bg-accent-green/10 border-accent-green/30'
}

function AlertsList() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchAlerts() {
      try {
        const response = await fetch(`${API_URL}/api/alerts?status=open&limit=50`)
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.statusText}`)
        }
        const data = await response.json()
        setAlerts(data.alerts || [])
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load alerts')
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
  }, [])

  if (loading) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-accent-cyan" />
        <p>Loading alerts...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p>Unable to load alerts. Make sure the backend is running.</p>
        <p className="text-sm mt-2 text-text-muted">Backend URL: {API_URL}</p>
        <p className="text-xs mt-1 text-accent-red">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {alerts.length === 0 ? (
        <div className="text-center py-12 text-text-secondary">
          No active alerts found
        </div>
      ) : (
        alerts.map((alert) => (
          <Link
            key={alert.alert_id}
            href={`/case?alert_id=${alert.alert_id}`}
            className="block p-5 bg-bg-secondary border border-border-default rounded-lg hover:border-accent-cyan/50 hover:bg-bg-tertiary transition-all duration-200 group"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <AlertTriangle className="h-5 w-5 text-accent-red" />
                  <h3 className="text-lg font-semibold font-mono text-text-primary">
                    {alert.account_id}
                  </h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(alert.risk_score)}`}>
                    {(alert.risk_score * 100).toFixed(0)}% Risk
                  </span>
                </div>
                <p className="text-sm text-text-secondary mb-3 line-clamp-2">
                  {alert.reason}
                </p>
                <div className="flex items-center gap-4 text-xs text-text-muted font-mono">
                  <span>ID: {alert.alert_id}</span>
                  <span className="capitalize px-2 py-0.5 bg-bg-tertiary rounded">
                    {alert.risk_bucket}
                  </span>
                </div>
              </div>
              <ArrowRight className="h-5 w-5 text-text-muted group-hover:text-accent-cyan transition-colors" />
            </div>
          </Link>
        ))
      )}
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="border-b border-border-default bg-bg-secondary/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-accent-cyan/10 rounded-lg">
              <Shield className="h-6 w-6 text-accent-cyan" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">
                Agentic Fraud Investigation
              </h1>
              <p className="text-sm text-text-secondary">
                LangGraph-powered fraud ring detection
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Stats Banner */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-bg-secondary border border-border-default rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent-red/10 rounded">
                <AlertTriangle className="h-5 w-5 text-accent-red" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">Active Alerts</p>
                <p className="text-sm text-text-muted">Pending investigation</p>
              </div>
            </div>
          </div>
          <div className="bg-bg-secondary border border-border-default rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent-cyan/10 rounded">
                <Activity className="h-5 w-5 text-accent-cyan" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">Graph Analysis</p>
                <p className="text-sm text-text-muted">Aerospike Graph + LangGraph</p>
              </div>
            </div>
          </div>
          <div className="bg-bg-secondary border border-border-default rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent-purple/10 rounded">
                <Shield className="h-5 w-5 text-accent-purple" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">AI-Powered</p>
                <p className="text-sm text-text-muted">Mistral reasoning</p>
              </div>
            </div>
          </div>
        </div>

        {/* Alerts Section */}
        <div className="bg-bg-secondary/30 border border-border-muted rounded-xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-accent-orange" />
              Open Fraud Alerts
            </h2>
            <span className="text-sm text-text-muted">
              Click an alert to start investigation
            </span>
          </div>
          
          <AlertsList />
        </div>
      </main>
    </div>
  )
}
