'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight, Terminal, Zap, Brain, Database } from 'lucide-react'
import { TraceEvent } from '@/lib/types'

interface TracePanelProps {
  events: TraceEvent[]
}

function getEventIcon(type: string) {
  switch (type) {
    case 'tool_call':
    case 'tool_result':
      return <Database className="h-3.5 w-3.5 text-accent-purple" />
    case 'decision':
      return <Brain className="h-3.5 w-3.5 text-accent-pink" />
    case 'graph_update':
      return <Zap className="h-3.5 w-3.5 text-accent-cyan" />
    default:
      return <Terminal className="h-3.5 w-3.5 text-accent-green" />
  }
}

function getEventColor(type: string): string {
  switch (type) {
    case 'tool_call':
      return 'border-accent-purple/30 bg-accent-purple/5'
    case 'tool_result':
      return 'border-accent-green/30 bg-accent-green/5'
    case 'decision':
      return 'border-accent-pink/30 bg-accent-pink/5'
    case 'graph_update':
      return 'border-accent-cyan/30 bg-accent-cyan/5'
    case 'score_update':
      return 'border-accent-orange/30 bg-accent-orange/5'
    default:
      return 'border-border-default bg-bg-tertiary'
  }
}

function TraceEventItem({ event, index }: { event: TraceEvent; index: number }) {
  const [expanded, setExpanded] = useState(false)
  
  const timestamp = new Date(event.timestamp).toLocaleTimeString()
  const hasData = event.data && Object.keys(event.data).length > 0
  
  return (
    <div className={`border rounded-md ${getEventColor(event.type)}`}>
      <button
        onClick={() => hasData && setExpanded(!expanded)}
        className="w-full p-2 flex items-center gap-2 text-left"
        disabled={!hasData}
      >
        {hasData ? (
          expanded ? (
            <ChevronDown className="h-3 w-3 text-text-muted" />
          ) : (
            <ChevronRight className="h-3 w-3 text-text-muted" />
          )
        ) : (
          <span className="w-3" />
        )}
        
        {getEventIcon(event.type)}
        
        <span className="flex-1 text-xs font-mono text-text-primary truncate">
          {event.node && <span className="text-accent-cyan">{event.node}</span>}
          {event.tool && <span className="text-accent-purple ml-1">→ {event.tool}</span>}
          {!event.node && !event.tool && event.type}
        </span>
        
        <span className="text-xs text-text-muted font-mono">
          {timestamp}
        </span>
      </button>
      
      {expanded && hasData && (
        <div className="px-3 pb-2 pt-0">
          <pre className="text-xs font-mono text-text-secondary bg-bg-primary/50 rounded p-2 overflow-x-auto max-h-40">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function TracePanel({ events }: TracePanelProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          <Terminal className="h-4 w-4 text-accent-green" />
          Trace Log
        </h3>
        <span className="text-xs text-text-muted font-mono">
          {events.length} events
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {events.length === 0 ? (
          <div className="text-center py-8 text-text-muted text-sm">
            Waiting for workflow events...
          </div>
        ) : (
          events.map((event, index) => (
            <TraceEventItem key={index} event={event} index={index} />
          ))
        )}
      </div>
    </div>
  )
}
