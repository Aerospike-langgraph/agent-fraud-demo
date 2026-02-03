'use client'

import { EvidenceSummary } from '@/lib/types'
import { Shield, Users, Server, Globe, TrendingUp, Search, AlertTriangle } from 'lucide-react'

interface EvidencePanelProps {
  evidence: EvidenceSummary | null
}

export default function EvidencePanel({ evidence }: EvidencePanelProps) {
  if (!evidence || !evidence.summary) {
    return (
      <div className="h-full flex items-center justify-center text-text-muted text-sm">
        Evidence will appear after analysis completes
      </div>
    )
  }

  const { summary, proof_bullets, shared_infrastructure, innocent_rationale } = evidence

  // Calculate detection percentage
  const detectionRate = summary.total_nodes_explored > 0 
    ? ((summary.ring_size / summary.total_nodes_explored) * 100).toFixed(1)
    : '0'

  return (
    <div className="h-full overflow-y-auto space-y-4 pr-1">
      {/* Exploration Summary - How fraud ring was detected */}
      <div className="bg-gradient-to-br from-accent-orange/10 to-accent-red/10 border border-accent-orange/30 rounded-lg p-3">
        <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
          <Search className="h-4 w-4 text-accent-orange" />
          Graph Exploration Summary
        </h4>
        <div className="space-y-2 text-sm text-text-secondary">
          <p>
            Explored <span className="text-accent-cyan font-semibold">{summary.total_nodes_explored}</span> accounts 
            {summary.total_edges_explored > 0 && (
              <> through <span className="text-accent-cyan font-semibold">{summary.total_edges_explored}</span> connections</>
            )}
          </p>
          <p>
            Identified <span className="text-accent-orange font-semibold">{summary.ring_size}</span> fraud ring members 
            (<span className="text-accent-orange">{detectionRate}%</span> of explored)
          </p>
          {summary.innocent_count > 0 && (
            <p>
              Cleared <span className="text-accent-green font-semibold">{summary.innocent_count}</span> accounts as innocent
            </p>
          )}
        </div>
      </div>

      {/* Detection Method Explanation */}
      <div className="bg-bg-tertiary border border-border-default rounded-lg p-3">
        <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-accent-yellow" />
          Detection Method
        </h4>
        <div className="space-y-2 text-xs text-text-secondary">
          <p>The fraud ring was detected through:</p>
          <ul className="space-y-1 ml-2">
            {summary.shared_device_count > 0 && (
              <li className="flex items-start gap-1">
                <span className="text-accent-cyan">•</span>
                <span><span className="text-accent-cyan font-semibold">{summary.shared_device_count}</span> shared device(s) linking multiple accounts</span>
              </li>
            )}
            {summary.shared_ip_count > 0 && (
              <li className="flex items-start gap-1">
                <span className="text-accent-purple">•</span>
                <span><span className="text-accent-purple font-semibold">{summary.shared_ip_count}</span> shared IP address(es) indicating same origin</span>
              </li>
            )}
            <li className="flex items-start gap-1">
              <span className="text-accent-orange">•</span>
              <span>Risk scoring above <span className="text-accent-orange font-semibold">80%</span> threshold (avg: {(summary.avg_ring_score * 100).toFixed(0)}%)</span>
            </li>
            {summary.ring_density > 0 && (
              <li className="flex items-start gap-1">
                <span className="text-accent-red">•</span>
                <span>High interconnection density ({(summary.ring_density * 100).toFixed(1)}%)</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-accent-red/10 border border-accent-red/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Users className="h-4 w-4 text-accent-red" />
            <span className="text-xs text-text-secondary">Fraud Ring</span>
          </div>
          <p className="text-2xl font-bold text-accent-red">{summary.ring_size}</p>
        </div>
        <div className="bg-accent-green/10 border border-accent-green/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Shield className="h-4 w-4 text-accent-green" />
            <span className="text-xs text-text-secondary">Innocent</span>
          </div>
          <p className="text-2xl font-bold text-accent-green">{summary.innocent_count}</p>
        </div>
        <div className="bg-accent-cyan/10 border border-accent-cyan/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Server className="h-4 w-4 text-accent-cyan" />
            <span className="text-xs text-text-secondary">Shared Devices</span>
          </div>
          <p className="text-2xl font-bold text-accent-cyan">{summary.shared_device_count}</p>
        </div>
        <div className="bg-accent-purple/10 border border-accent-purple/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Globe className="h-4 w-4 text-accent-purple" />
            <span className="text-xs text-text-secondary">Shared IPs</span>
          </div>
          <p className="text-2xl font-bold text-accent-purple">{summary.shared_ip_count}</p>
        </div>
      </div>

      {/* Ring Metrics */}
      <div className="bg-bg-tertiary border border-border-default rounded-lg p-3">
        <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-accent-orange" />
          Ring Metrics
        </h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Ring Density</span>
            <span className="font-mono text-text-primary">
              {(summary.ring_density * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Avg Ring Score</span>
            <span className="font-mono text-accent-red">
              {(summary.avg_ring_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Avg Innocent Score</span>
            <span className="font-mono text-accent-green">
              {(summary.avg_innocent_score * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Nodes Explored</span>
            <span className="font-mono text-text-primary">
              {summary.total_nodes_explored}
            </span>
          </div>
        </div>
      </div>

      {/* Proof Bullets */}
      {proof_bullets && proof_bullets.length > 0 && (
        <div className="bg-bg-tertiary border border-border-default rounded-lg p-3">
          <h4 className="text-sm font-semibold text-text-primary mb-2">
            Key Findings
          </h4>
          <ul className="space-y-2">
            {proof_bullets.map((bullet, i) => (
              <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                <span className="text-accent-cyan mt-1">•</span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Shared Infrastructure */}
      {shared_infrastructure && (
        <div className="bg-bg-tertiary border border-border-default rounded-lg p-3">
          <h4 className="text-sm font-semibold text-text-primary mb-2">
            Shared Infrastructure
          </h4>
          
          {shared_infrastructure.devices?.devices?.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-text-muted mb-1">Devices</p>
              <div className="space-y-1">
                {shared_infrastructure.devices.devices.slice(0, 5).map((d, i) => (
                  <div key={i} className="flex justify-between text-xs font-mono">
                    <span className="text-text-secondary truncate max-w-[150px]">{d.id}</span>
                    <span className="text-accent-cyan">{d.ring_users} users</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {shared_infrastructure.ips?.ips?.length > 0 && (
            <div>
              <p className="text-xs text-text-muted mb-1">IP Addresses</p>
              <div className="space-y-1">
                {shared_infrastructure.ips.ips.slice(0, 5).map((ip, i) => (
                  <div key={i} className="flex justify-between text-xs font-mono">
                    <span className="text-text-secondary truncate max-w-[150px]">{ip.id}</span>
                    <span className="text-accent-purple">{ip.ring_users} users</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
