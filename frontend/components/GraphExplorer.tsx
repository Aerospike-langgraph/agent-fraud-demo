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
  onNodeClick?: (node: GraphNode) => void
}

function getNodeColor(node: GraphNode, suspectId?: string, fraudRingIds?: string[]): string {
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

function getNodeSize(node: GraphNode, suspectId?: string): number {
  if (node.id === suspectId) return 12
  if (node.type === 'suspect') return 12
  if (node.type === 'ring_candidate') return 8
  if (node.label === 'device' || node.label === 'ip') return 5
  return 6
}

export default function GraphExplorer({
  nodes,
  edges,
  suspectId,
  fraudRingIds = [],
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
  
  // Configure forces
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(-150)
      fgRef.current.d3Force('link')?.distance(60)
    }
  }, [])
  
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
  
  const graphData = {
    nodes: nodes.map((n) => ({
      ...n,
      color: getNodeColor(n, suspectId, fraudRingIds),
      val: getNodeSize(n, suspectId)
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
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#f85149]" />
            <span className="text-text-secondary">Suspect</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#d29922]" />
            <span className="text-text-secondary">Fraud Ring</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#58a6ff]" />
            <span className="text-text-secondary">Device</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#3fb950]" />
            <span className="text-text-secondary">IP</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#8b949e]" />
            <span className="text-text-secondary">Innocent</span>
          </div>
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
          linkColor={() => '#586069'}
          linkWidth={2}
          linkDirectionalArrowLength={0}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.1}
          onNodeClick={(node: any) => onNodeClick?.(node)}
          cooldownTicks={100}
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
