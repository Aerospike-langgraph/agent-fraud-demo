'use client'

import { EvidenceSummary } from '@/lib/types'
import { Shield, Users, Server, Globe, TrendingUp } from 'lucide-react'

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

  return (
    <div className="h-full overflow-y-auto space-y-4 pr-1">
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
