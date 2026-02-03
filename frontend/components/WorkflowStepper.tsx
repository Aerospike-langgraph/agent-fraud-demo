'use client'

import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react'
import { WorkflowNode } from '@/lib/types'

interface WorkflowStepperProps {
  nodes: WorkflowNode[]
  currentNode: string
  isComplete?: boolean
}

const WORKFLOW_STEPS: WorkflowNode[] = [
  { id: 'load_context', label: 'Load Context', description: 'Initialize investigation', status: 'pending' },
  { id: 'traverse_graph', label: 'Traverse Graph', description: 'Expand from frontier', status: 'pending' },
  { id: 'score_neighbors', label: 'Score Neighbors', description: 'Calculate risk scores', status: 'pending' },
  { id: 'select_candidates', label: 'Select Candidates', description: 'Choose high-risk accounts', status: 'pending' },
  { id: 'decide_expand', label: 'Decide Expand', description: 'LLM reasoning', status: 'pending' },
  { id: 'build_subgraph', label: 'Build Subgraph', description: 'Construct fraud ring', status: 'pending' },
  { id: 'build_evidence', label: 'Build Evidence', description: 'Generate proof', status: 'pending' },
  { id: 'generate_report', label: 'Generate Report', description: 'AI report synthesis', status: 'pending' },
]

export default function WorkflowStepper({ nodes, currentNode, isComplete = false }: WorkflowStepperProps) {
  // Merge provided nodes with defaults
  const steps = WORKFLOW_STEPS.map((step) => {
    const provided = nodes.find((n) => n.id === step.id)
    return provided || step
  })

  // Determine step status based on currentNode
  const currentIndex = steps.findIndex((s) => s.id === currentNode)
  
  const getStepStatus = (index: number, step: WorkflowNode): 'completed' | 'active' | 'pending' | 'error' => {
    // If workflow is complete, all steps are completed
    if (isComplete) return 'completed'
    
    if (step.status === 'error') return 'error'
    if (step.status === 'completed') return 'completed'
    if (index < currentIndex) return 'completed'
    if (index === currentIndex) return 'active'
    return 'pending'
  }

  return (
    <div className="bg-bg-secondary border border-border-default rounded-lg p-4 h-full">
      <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-accent-cyan animate-pulse" />
        Workflow Progress
      </h3>
      
      <div className="space-y-1">
        {steps.map((step, index) => {
          const status = getStepStatus(index, step)
          
          return (
            <div key={step.id} className="relative">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div 
                  className={`absolute left-[11px] top-[24px] w-0.5 h-8 transition-colors duration-300 ${
                    status === 'completed' ? 'bg-accent-green' :
                    status === 'active' ? 'bg-accent-cyan/50' :
                    'bg-border-default'
                  }`}
                />
              )}
              
              <div className={`flex items-start gap-3 p-2 rounded-md transition-all duration-200 ${
                status === 'active' ? 'bg-accent-cyan/10' : ''
              }`}>
                {/* Status icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {status === 'completed' && (
                    <CheckCircle className="h-5 w-5 text-accent-green" />
                  )}
                  {status === 'active' && (
                    <Loader2 className="h-5 w-5 text-accent-cyan animate-spin" />
                  )}
                  {status === 'pending' && (
                    <Circle className="h-5 w-5 text-text-muted" />
                  )}
                  {status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-accent-red" />
                  )}
                </div>
                
                {/* Step info */}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${
                    status === 'active' ? 'text-accent-cyan' :
                    status === 'completed' ? 'text-text-primary' :
                    'text-text-muted'
                  }`}>
                    {step.label}
                  </p>
                  <p className="text-xs text-text-muted truncate">
                    {step.description}
                  </p>
                  {step.duration && (
                    <p className="text-xs text-text-muted mt-0.5">
                      {step.duration}ms
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
