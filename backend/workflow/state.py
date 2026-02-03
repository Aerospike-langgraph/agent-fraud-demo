"""
GraphState - LangGraph state definition for fraud investigation workflow.

This state is checkpointed at each node transition, enabling:
- Pause/resume of investigations
- Human-in-the-loop review gates
- Full audit trail of agent decisions
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class NodeInfo(TypedDict):
    """Graph node representation for visualization."""
    id: str
    label: str  # account, device, ip, user
    type: str   # suspect, ring_candidate, innocent, background
    properties: Dict[str, Any]


class EdgeInfo(TypedDict):
    """Graph edge representation for visualization."""
    source: str
    target: str
    edge_type: str  # USES_DEVICE, USES_IP, TRANSACTS
    properties: Dict[str, Any]


class AccountScore(TypedDict):
    """Risk score for a single account."""
    account_id: str
    score: float  # 0.0 - 1.0
    bucket: str   # low, medium, high, critical
    reasons: List[Dict[str, Any]]  # [{code, weight, description}]
    evidence: Dict[str, Any]  # {shared_devices, shared_ips, burst_tx, ...}


class ExpandDecision(TypedDict):
    """Decision output from DecideExpand node."""
    should_expand: bool
    next_edge_types: List[str]  # ["device", "ip", "tx"]
    reason: str
    llm_reasoning: str  # Full LLM reasoning for trace panel


class GraphState(TypedDict):
    """
    Main state for the fraud investigation LangGraph workflow.
    
    All fields must be serializable for Aerospike checkpointing.
    """
    # Case identification
    case_id: str
    alert_id: str
    suspect_account_id: str
    
    # Traversal budget and cost tracking
    max_nodes: int           # Hard cap on total nodes to explore
    max_edges: int           # Hard cap on total edges
    max_hops_cap: int        # Maximum depth (e.g., 3)
    current_hop: int         # Current expansion depth
    estimated_cost: float    # Accumulated cost from traversals
    cost_budget: float       # Maximum cost allowed (e.g., 1.0)
    
    # Graph artifacts - using Annotated with add for incremental updates
    seen_nodes: Annotated[List[str], add]      # Node IDs we've visited
    seen_edges: Annotated[List[str], add]      # Edge IDs we've seen
    frontier_accounts: List[str]               # Accounts to expand next
    
    # Subgraph for visualization
    subgraph_nodes: Annotated[List[NodeInfo], add]
    subgraph_edges: Annotated[List[EdgeInfo], add]
    
    # Scoring artifacts
    scores: Dict[str, AccountScore]  # account_id -> score info
    ranked_accounts: List[str]       # Account IDs sorted by risk
    
    # Decisions and reasoning
    expand_decision: Optional[ExpandDecision]
    decisions_history: Annotated[List[Dict[str, Any]], add]  # All decisions made
    
    # Final outputs
    fraud_ring_nodes: List[str]       # Final fraud ring member IDs
    fraud_ring_edges: List[str]       # Edges within fraud ring
    innocent_neighbors: List[str]     # Accounts determined innocent
    evidence_summary: Dict[str, Any]  # Proof metrics
    report_markdown: str              # Final investigation report
    
    # Workflow control
    current_node: str                 # Current LangGraph node name
    workflow_status: str              # running, paused, completed, error
    error_message: Optional[str]
    
    # Trace events for UI
    trace_events: Annotated[List[Dict[str, Any]], add]


def create_initial_state(
    case_id: str,
    alert_id: str,
    suspect_account_id: str,
    max_nodes: int = 500,
    max_edges: int = 1000,
    max_hops_cap: int = 10,
    cost_budget: float = 50.0
) -> GraphState:
    """Create initial state for a new investigation."""
    return GraphState(
        # Case identification
        case_id=case_id,
        alert_id=alert_id,
        suspect_account_id=suspect_account_id,
        
        # Traversal budget
        max_nodes=max_nodes,
        max_edges=max_edges,
        max_hops_cap=max_hops_cap,
        current_hop=0,
        estimated_cost=0.0,
        cost_budget=cost_budget,
        
        # Graph artifacts
        seen_nodes=[],
        seen_edges=[],
        frontier_accounts=[suspect_account_id],
        
        # Subgraph
        subgraph_nodes=[],
        subgraph_edges=[],
        
        # Scoring
        scores={},
        ranked_accounts=[],
        
        # Decisions
        expand_decision=None,
        decisions_history=[],
        
        # Outputs
        fraud_ring_nodes=[],
        fraud_ring_edges=[],
        innocent_neighbors=[],
        evidence_summary={},
        report_markdown="",
        
        # Workflow control
        current_node="start",
        workflow_status="running",
        error_message=None,
        
        # Trace
        trace_events=[]
    )
