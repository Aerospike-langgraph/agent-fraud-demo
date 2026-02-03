'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { GraphNode, GraphEdge } from '@/lib/types'
import { ZoomIn, ZoomOut, Maximize2, Focus } from 'lucide-react'

// Dynamic import to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center text-text-muted">
      Loading graph...
    </div>
  )
})

interface GraphExplorerProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  suspectId?: string
  fraudRingIds?: string[]
  viewMode?: 'full' | 'fraud_ring'
  onNodeClick?: (node: GraphNode) => void
}

function getNodeColor(
  node: GraphNode, 
  suspectId?: string, 
  fraudRingIds?: string[],
  viewMode: 'full' | 'fraud_ring' = 'full'
): string {
  const isFraudRingMember = node.id === suspectId || 
    fraudRingIds?.includes(node.id) ||
    node.type === 'suspect' ||
    node.type === 'ring_candidate' ||
    node.type === 'ring_infrastructure'
  
  // In full view mode, dim non-fraud-ring nodes
  if (viewMode === 'full' && !isFraudRingMember) {
    switch (node.type) {
      case 'innocent':
        return '#484f58' // Dimmed gray
      case 'device':
        return '#2d4a6e' // Dimmed blue
      case 'ip':
        return '#2d5a3e' // Dimmed green
      default:
        return '#3d444d' // Dimmed default
    }
  }
  
  // Highlight fraud ring members
  if (node.id === suspectId) return '#f85149' // Red for suspect
  if (fraudRingIds?.includes(node.id)) return '#d29922' // Orange for ring members
  
  switch (node.type) {
    case 'suspect':
      return '#f85149'
    case 'ring_candidate':
    case 'ring_infrastructure':
      return '#d29922'
    case 'innocent':
      return '#8b949e'
    case 'device':
      return '#58a6ff'
    case 'ip':
      return '#3fb950'
    default:
      return '#6e7681'
  }
}

function getNodeSize(
  node: GraphNode, 
  suspectId?: string,
  fraudRingIds?: string[],
  viewMode: 'full' | 'fraud_ring' = 'full',
  totalNodes: number = 0
): number {
  const isFraudRingMember = node.id === suspectId || 
    fraudRingIds?.includes(node.id) ||
    node.type === 'suspect' ||
    node.type === 'ring_candidate'
  
  // In full view mode with many nodes, make innocent nodes tiny (like dust)
  if (viewMode === 'full') {
    // Scale sizes based on total node count for better visualization
    const hasLargeGraph = totalNodes > 100
    
    if (node.id === suspectId || node.type === 'suspect') {
      return hasLargeGraph ? 20 : 14  // Big prominent suspect
    }
    if (isFraudRingMember || node.type === 'ring_candidate') {
      return hasLargeGraph ? 12 : 10  // Large fraud ring members
    }
    if (node.type === 'ring_infrastructure') {
      return hasLargeGraph ? 8 : 7  // Medium infrastructure
    }
    // Innocent nodes - very small in large graphs
    if (node.label === 'device' || node.type === 'device') return hasLargeGraph ? 1 : 4
    if (node.label === 'ip' || node.type === 'ip') return hasLargeGraph ? 1 : 4
    return hasLargeGraph ? 1 : 3  // Tiny dots for innocents in large graphs
  }
  
  // Fraud ring view - normal sizing
  if (node.id === suspectId || node.type === 'suspect') return 12
  if (node.type === 'ring_candidate') return 8
  if (node.type === 'ring_infrastructure') return 6
  if (node.label === 'device' || node.label === 'ip') return 5
  return 6
}

export default function GraphExplorer({
  nodes,
  edges,
  suspectId,
  fraudRingIds = [],
  viewMode = 'full',
  onNodeClick
}: GraphExplorerProps) {
  const fgRef = useRef<any>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        })
      }
    }
    
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])
  
  // Configure forces - adapt to graph size
  useEffect(() => {
    if (fgRef.current) {
      const nodeCount = nodes.length
      // For large graphs, use weaker forces to prevent chaos
      if (nodeCount > 500) {
        fgRef.current.d3Force('charge')?.strength(-30)
        fgRef.current.d3Force('link')?.distance(20)
      } else if (nodeCount > 100) {
        fgRef.current.d3Force('charge')?.strength(-80)
        fgRef.current.d3Force('link')?.distance(40)
      } else {
        fgRef.current.d3Force('charge')?.strength(-150)
        fgRef.current.d3Force('link')?.distance(60)
      }
    }
  }, [nodes.length])
  
  // Prepare graph data
  const nodeIds = new Set(nodes.map(n => n.id))
  
  // Filter edges to only those with valid source and target nodes
  const validEdges = edges.filter(e => {
    const hasSource = nodeIds.has(e.source)
    const hasTarget = nodeIds.has(e.target)
    if (!hasSource || !hasTarget) {
      console.warn(`Invalid edge: ${e.source} -> ${e.target} (source: ${hasSource}, target: ${hasTarget})`)
    }
    return hasSource && hasTarget
  })
  
  const totalNodes = nodes.length
  
  const graphData = {
    nodes: nodes.map((n) => ({
      ...n,
      color: getNodeColor(n, suspectId, fraudRingIds, viewMode),
      val: getNodeSize(n, suspectId, fraudRingIds, viewMode, totalNodes)
    })),
    links: validEdges.map((e) => ({
      source: e.source,
      target: e.target,
      edgeType: e.edge_type
    }))
  }
  
  const handleZoomIn = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom()
      fgRef.current.zoom(currentZoom * 1.3, 400)
    }
  }
  
  const handleZoomOut = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom()
      fgRef.current.zoom(currentZoom / 1.3, 400)
    }
  }
  
  const handleFit = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 50)
    }
  }
  
  const handleFocusSuspect = () => {
    if (fgRef.current && suspectId) {
      const node = graphData.nodes.find((n) => n.id === suspectId) as any
      if (node && node.x !== undefined && node.y !== undefined) {
        fgRef.current.centerAt(node.x, node.y, 400)
        fgRef.current.zoom(2, 400)
      }
    }
  }

  return (
    <div ref={containerRef} className="relative w-full h-full bg-bg-secondary rounded-lg overflow-hidden">
      {/* Controls */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-bg-tertiary hover:bg-bg-elevated border border-border-default rounded transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4 text-text-secondary" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-bg-tertiary hover:bg-bg-elevated border border-border-default rounded transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4 text-text-secondary" />
        </button>
        <button
          onClick={handleFit}
          className="p-2 bg-bg-tertiary hover:bg-bg-elevated border border-border-default rounded transition-colors"
          title="Fit to View"
        >
          <Maximize2 className="h-4 w-4 text-text-secondary" />
        </button>
        {suspectId && (
          <button
            onClick={handleFocusSuspect}
            className="p-2 bg-accent-red/20 hover:bg-accent-red/30 border border-accent-red/30 rounded transition-colors"
            title="Focus Suspect"
          >
            <Focus className="h-4 w-4 text-accent-red" />
          </button>
        )}
      </div>
      
      {/* Legend */}
      <div className="absolute bottom-3 left-3 z-10 bg-bg-tertiary/90 backdrop-blur-sm border border-border-default rounded p-2">
        <div className="text-xs font-mono space-y-1">
          <div className="text-text-muted mb-1 border-b border-border-default pb-1">
            {viewMode === 'full' ? 'Full Exploration' : 'Fraud Ring View'}
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#f85149]" />
            <span className="text-text-secondary">Suspect</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#d29922]" />
            <span className="text-text-secondary">Fraud Ring</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${viewMode === 'full' ? 'bg-[#2d4a6e]' : 'bg-[#58a6ff]'}`} />
            <span className="text-text-secondary">Device</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${viewMode === 'full' ? 'bg-[#2d5a3e]' : 'bg-[#3fb950]'}`} />
            <span className="text-text-secondary">IP</span>
          </div>
          {viewMode === 'full' && (
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-[#484f58]" />
              <span className="text-text-secondary">Innocent</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Stats */}
      <div className="absolute top-3 left-3 z-10 bg-bg-tertiary/90 backdrop-blur-sm border border-border-default rounded px-3 py-2">
        <div className="text-xs font-mono text-text-secondary">
          <span className="text-accent-cyan">{nodes.length}</span> nodes · 
          <span className="text-accent-green ml-1">{validEdges.length}</span> edges
          {validEdges.length !== edges.length && (
            <span className="text-accent-yellow ml-1">({edges.length - validEdges.length} invalid)</span>
          )}
        </div>
      </div>
      
      {/* Graph */}
      {nodes.length > 0 ? (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="#161b22"
          nodeLabel={(node: any) => `${node.label}: ${node.id}`}
          nodeColor={(node: any) => node.color}
          nodeVal={(node: any) => node.val}
          linkColor={(link: any) => {
            // In full view mode, highlight fraud ring connections
            if (viewMode === 'full') {
              const sourceNode = graphData.nodes.find((n: any) => n.id === link.source || n.id === link.source?.id)
              const targetNode = graphData.nodes.find((n: any) => n.id === link.target || n.id === link.target?.id)
              const sourceInRing = sourceNode && (
                sourceNode.id === suspectId || 
                fraudRingIds.includes(sourceNode.id) ||
                ['suspect', 'ring_candidate', 'ring_infrastructure'].includes(sourceNode.type)
              )
              const targetInRing = targetNode && (
                targetNode.id === suspectId || 
                fraudRingIds.includes(targetNode.id) ||
                ['suspect', 'ring_candidate', 'ring_infrastructure'].includes(targetNode.type)
              )
              if (sourceInRing && targetInRing) {
                return '#d29922' // Orange for fraud ring connections
              }
              // For large graphs, make non-ring edges very dim
              return totalNodes > 100 ? '#1c2128' : '#30363d'
            }
            return '#586069'
          }}
          linkWidth={(link: any) => {
            if (viewMode === 'full') {
              const sourceNode = graphData.nodes.find((n: any) => n.id === link.source || n.id === link.source?.id)
              const targetNode = graphData.nodes.find((n: any) => n.id === link.target || n.id === link.target?.id)
              const sourceInRing = sourceNode && (
                sourceNode.id === suspectId || 
                fraudRingIds.includes(sourceNode.id) ||
                ['suspect', 'ring_candidate', 'ring_infrastructure'].includes(sourceNode.type)
              )
              const targetInRing = targetNode && (
                targetNode.id === suspectId || 
                fraudRingIds.includes(targetNode.id) ||
                ['suspect', 'ring_candidate', 'ring_infrastructure'].includes(targetNode.type)
              )
              if (sourceInRing && targetInRing) {
                return totalNodes > 100 ? 4 : 3 // Thicker for fraud ring connections
              }
              return totalNodes > 100 ? 0.3 : 1 // Very thin for other connections in large graphs
            }
            return 2
          }}
          linkDirectionalArrowLength={0}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.1}
          onNodeClick={(node: any) => onNodeClick?.(node)}
          cooldownTicks={totalNodes > 500 ? 50 : totalNodes > 100 ? 75 : 100}
          warmupTicks={totalNodes > 500 ? 50 : 0}
          onNodeHover={(node: any) => {
            document.body.style.cursor = node ? 'pointer' : 'default'
          }}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-text-muted">
          <div className="text-center">
            <p className="text-sm">No graph data yet</p>
            <p className="text-xs mt-1">Start the investigation to see the graph</p>
          </div>
        </div>
      )}
    </div>
  )
}
