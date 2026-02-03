// API Types

export interface Alert {
  alert_id: string;
  account_id: string;
  created_at: string;
  risk_score: number;
  risk_bucket: string;
  reason: string;
  status: string;
}

export interface Case {
  case_id: string;
  alert_id: string;
  suspect_account_id: string;
  status: string;
  workflow_status?: string;
  current_node: string;
  current_hop: number;
  estimated_cost: number;
  nodes_explored: number;
  fraud_ring_size: number;
  fraud_ring_nodes?: string[];
  innocent_count: number;
  subgraph: SubgraphData;
  scores: Record<string, AccountScore>;
  evidence_summary: EvidenceSummary;
  report_markdown: string;
}

export interface SubgraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
  properties: Record<string, any>;
}

export interface AccountScore {
  account_id: string;
  score: number;
  bucket: string;
  reasons: ScoreReason[];
  evidence: Record<string, any>;
}

export interface ScoreReason {
  code: string;
  weight: number;
  description: string;
}

export interface EvidenceSummary {
  summary: {
    ring_size: number;
    innocent_count: number;
    total_nodes_explored: number;
    total_edges_explored: number;
    shared_device_count: number;
    shared_ip_count: number;
    ring_density: number;
    avg_ring_score: number;
    avg_innocent_score: number;
  };
  proof_bullets: string[];
  shared_infrastructure: {
    devices: { devices: Array<{ id: string; ring_users: number }> };
    ips: { ips: Array<{ id: string; ring_users: number }> };
  };
  innocent_rationale: Array<{
    account_id: string;
    score: number;
    reason: string;
  }>;
}

// SSE Event Types
export interface SSEEvent {
  type: string;
  node: string;
  timestamp: string;
  data: Record<string, any>;
  tool?: string;
  artifact_type?: string;
}

export interface TraceEvent extends SSEEvent {
  type: 'node_start' | 'node_end' | 'tool_call' | 'tool_result' | 'graph_update' | 'score_update' | 'decision' | 'artifact';
}

// Workflow Types
export interface WorkflowNode {
  id: string;
  label: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  duration?: number;
}

export interface WorkflowStructure {
  nodes: Array<{
    id: string;
    label: string;
    description: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    condition?: string;
  }>;
}
