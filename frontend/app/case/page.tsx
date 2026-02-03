'use client'

import { Suspense, useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Play, RefreshCw, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

import { getAlert, startCase, getCase, runCase } from '@/lib/api'
import { useSSE } from '@/hooks/useSSE'
import { Alert, Case, TraceEvent, WorkflowNode } from '@/lib/types'

import WorkflowStepper from '@/components/WorkflowStepper'
import GraphExplorer from '@/components/GraphExplorer'
import TracePanel from '@/components/TracePanel'
import EvidencePanel from '@/components/EvidencePanel'
import ReportPanel from '@/components/ReportPanel'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000'

type TabType = 'trace' | 'evidence' | 'report'

function CasePageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const alertId = searchParams.get('alert_id')
  const caseIdParam = searchParams.get('case_id')
  
  const [alert, setAlert] = useState<Alert | null>(null)
  const [caseData, setCaseData] = useState<Case | null>(null)
  const [caseId, setCaseId] = useState<string | null>(caseIdParam)
  const [workflowStatus, setWorkflowStatus] = useState<'idle' | 'starting' | 'running' | 'completed' | 'error'>('idle')
  const [activeTab, setActiveTab] = useState<TabType>('trace')
  const [workflowNodes, setWorkflowNodes] = useState<WorkflowNode[]>([])
  const [error, setError] = useState<string | null>(null)
  
  // SSE for real-time updates
  const sseUrl = caseId && workflowStatus === 'running' ? `${API_URL}/api/case/${caseId}/stream` : null
  
  const handleSSEEvent = useCallback((event: TraceEvent) => {
    // Update workflow nodes based on events
    if (event.type === 'node_start' || event.type === 'node_end') {
      setWorkflowNodes(prev => {
        const existing = prev.find(n => n.id === event.node)
        if (existing) {
          return prev.map(n => 
            n.id === event.node 
              ? { ...n, status: event.type === 'node_start' ? 'active' : 'completed' }
              : n
          )
        }
        return [...prev, {
          id: event.node,
          label: event.node.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          description: '',
          status: event.type === 'node_start' ? 'active' : 'completed'
        }]
      })
    }
  }, [])
  
  const handleSSEComplete = useCallback((data: any) => {
    setWorkflowStatus('completed')
    // Refresh case data
    if (caseId) {
      getCase(caseId).then(setCaseData).catch(console.error)
    }
  }, [caseId])
  
  const { events, isConnected, isComplete, connect, disconnect } = useSSE(sseUrl, {
    onEvent: handleSSEEvent,
    onComplete: handleSSEComplete
  })
  
  // Load alert data
  useEffect(() => {
    if (alertId) {
      getAlert(alertId)
        .then(setAlert)
        .catch(err => setError(`Failed to load alert: ${err.message}`))
    }
  }, [alertId])
  
  // Load existing case if case_id provided
  useEffect(() => {
    if (caseIdParam) {
      getCase(caseIdParam)
        .then(data => {
          if (data) {
            setCaseData(data)
            setCaseId(caseIdParam)
            if (data.workflow_status === 'completed') {
              setWorkflowStatus('completed')
            }
          }
        })
        .catch(console.error)
    }
  }, [caseIdParam])
  
  // Start investigation
  const handleStartInvestigation = async () => {
    if (!alertId) return
    
    setWorkflowStatus('starting')
    setError(null)
    
    try {
      // Create case - generous limits to let LLM decide when to stop
      const newCase = await startCase({
        alert_id: alertId,
        max_hops: 10,        // High limit - LLM decides actual stopping point
        cost_budget: 50.0,   // High budget - LLM decides based on value
        max_nodes: 500       // High limit - explore thoroughly
      })
      
      setCaseId(newCase.case_id)
      
      // Start workflow
      await runCase(newCase.case_id)
      setWorkflowStatus('running')
      
      // Update URL
      router.replace(`/case?alert_id=${alertId}&case_id=${newCase.case_id}`)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start investigation')
      setWorkflowStatus('error')
    }
  }
  
  // Connect to SSE when running
  useEffect(() => {
    if (workflowStatus === 'running' && sseUrl) {
      connect()
    }
    return () => disconnect()
  }, [workflowStatus, sseUrl, connect, disconnect])
  
  // Refresh case data periodically when running
  useEffect(() => {
    if (workflowStatus !== 'running' || !caseId) return
    
    const interval = setInterval(() => {
      getCase(caseId).then(data => {
        setCaseData(data)
        // Auto-detect completion from backend status
        if (data?.workflow_status === 'completed' || data?.status === 'completed') {
          setWorkflowStatus('completed')
        }
      }).catch(console.error)
    }, 2000)
    
    return () => clearInterval(interval)
  }, [workflowStatus, caseId])
  
  if (!alertId) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="text-center">
          <p className="text-text-secondary mb-4">No alert selected</p>
          <Link href="/" className="text-accent-cyan hover:underline">
            Return to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-bg-primary flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-border-default bg-bg-secondary px-4 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-text-muted hover:text-text-primary transition-colors">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-lg font-semibold text-text-primary">
                Investigation: {alert?.account_id || alertId}
              </h1>
              <p className="text-sm text-text-muted font-mono">
                {caseId || 'New investigation'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Status indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-bg-tertiary rounded-full">
              {workflowStatus === 'idle' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-text-muted" />
                  <span className="text-sm text-text-secondary">Ready</span>
                </>
              )}
              {workflowStatus === 'starting' && (
                <>
                  <RefreshCw className="w-4 h-4 text-accent-cyan animate-spin" />
                  <span className="text-sm text-accent-cyan">Starting...</span>
                </>
              )}
              {workflowStatus === 'running' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" />
                  <span className="text-sm text-accent-cyan">Running</span>
                </>
              )}
              {workflowStatus === 'completed' && (
                <>
                  <CheckCircle className="w-4 h-4 text-accent-green" />
                  <span className="text-sm text-accent-green">Completed</span>
                </>
              )}
              {workflowStatus === 'error' && (
                <>
                  <AlertCircle className="w-4 h-4 text-accent-red" />
                  <span className="text-sm text-accent-red">Error</span>
                </>
              )}
            </div>
            
            {/* Start button */}
            {workflowStatus === 'idle' && (
              <button
                onClick={handleStartInvestigation}
                className="flex items-center gap-2 px-4 py-2 bg-accent-cyan text-bg-primary font-medium rounded-lg hover:bg-accent-cyan/90 transition-colors"
              >
                <Play className="h-4 w-4" />
                Start Investigation
              </button>
            )}
          </div>
        </div>
        
        {error && (
          <div className="mt-2 p-2 bg-accent-red/10 border border-accent-red/30 rounded text-sm text-accent-red">
            {error}
          </div>
        )}
      </header>
      
      {/* Main content - 3 column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Workflow Stepper */}
        <div className="w-64 border-r border-border-default p-3 overflow-y-auto flex-shrink-0">
          <WorkflowStepper 
            nodes={workflowNodes}
            currentNode={caseData?.current_node || ''}
            isComplete={workflowStatus === 'completed'}
          />
        </div>
        
        {/* Center: Graph */}
        <div className="flex-1 p-3 min-w-0">
          <GraphExplorer
            nodes={caseData?.subgraph?.nodes || []}
            edges={caseData?.subgraph?.edges || []}
            suspectId={alert?.account_id}
            fraudRingIds={caseData?.fraud_ring_nodes || []}
          />
        </div>
        
        {/* Right: Tabs (Trace/Evidence/Report) */}
        <div className="w-96 border-l border-border-default flex flex-col flex-shrink-0">
          {/* Tab buttons */}
          <div className="flex border-b border-border-default flex-shrink-0">
            {(['trace', 'evidence', 'report'] as TabType[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-accent-cyan border-b-2 border-accent-cyan bg-accent-cyan/5'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
          
          {/* Tab content */}
          <div className="flex-1 p-3 overflow-hidden">
            {activeTab === 'trace' && <TracePanel events={events} />}
            {activeTab === 'evidence' && <EvidencePanel evidence={caseData?.evidence_summary || null} />}
            {activeTab === 'report' && <ReportPanel markdown={caseData?.report_markdown || ''} />}
          </div>
        </div>
      </div>
    </div>
  )
}

// Loading fallback component
function CasePageLoading() {
  return (
    <div className="h-screen bg-bg-primary flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 text-accent-cyan animate-spin" />
        <p className="text-text-secondary">Loading investigation...</p>
      </div>
    </div>
  )
}

// Main page export with Suspense boundary
export default function CasePage() {
  return (
    <Suspense fallback={<CasePageLoading />}>
      <CasePageContent />
    </Suspense>
  )
}
