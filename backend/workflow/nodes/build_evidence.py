"""
BuildEvidence Node - Generate evidence summary using EvidenceTool.

Analyzes the fraud ring and generates:
- Proof metrics (shared devices, IPs, transactions)
- Evidence bullets for report
- Innocent account rationale
"""

import logging
from datetime import datetime
from typing import Dict, Any

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.build_evidence")


def build_evidence_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build evidence summary using EvidenceTool.
    
    Args:
        state: Current graph state
        services: Dict with evidence_tool
        
    Returns:
        State updates with evidence_summary
    """
    evidence_tool = services.get("evidence_tool")
    
    fraud_ring_nodes = state.get("fraud_ring_nodes", [])
    innocent_nodes = state.get("innocent_neighbors", [])
    subgraph_nodes = state.get("subgraph_nodes", [])
    subgraph_edges = state.get("subgraph_edges", [])
    scores = state.get("scores", {})
    suspect_account_id = state["suspect_account_id"]
    
    logger.info(
        f"BuildEvidence: {len(fraud_ring_nodes)} ring members, "
        f"{len(innocent_nodes)} innocents"
    )
    
    # Create trace event for tool call
    trace_tool_call = {
        "type": "tool_call",
        "node": "build_evidence",
        "tool": "build_evidence",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "ring_size": len(fraud_ring_nodes),
            "innocent_size": len(innocent_nodes)
        }
    }
    
    # Call evidence tool
    result = evidence_tool.invoke(
        fraud_ring_nodes=fraud_ring_nodes,
        innocent_nodes=innocent_nodes,
        subgraph_nodes=subgraph_nodes,
        subgraph_edges=subgraph_edges,
        scores=scores,
        suspect_account_id=suspect_account_id
    )
    
    evidence_summary = {
        "summary": result.get("summary", {}),
        "proof_bullets": result.get("proof_bullets", []),
        "shared_infrastructure": result.get("shared_infrastructure", {}),
        "innocent_rationale": result.get("innocent_rationale", []),
        "ring_connections": result.get("ring_connections", {})
    }
    
    # Create trace events
    trace_tool_result = {
        "type": "tool_result",
        "node": "build_evidence",
        "tool": "build_evidence",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "proof_bullets_count": len(evidence_summary["proof_bullets"]),
            "shared_devices": len(evidence_summary.get("shared_infrastructure", {}).get("devices", {}).get("devices", [])),
            "shared_ips": len(evidence_summary.get("shared_infrastructure", {}).get("ips", {}).get("ips", []))
        }
    }
    
    trace_artifact = {
        "type": "artifact",
        "artifact_type": "evidence_summary",
        "node": "build_evidence",
        "timestamp": datetime.now().isoformat(),
        "data": evidence_summary.get("summary", {})
    }
    
    logger.info(
        f"BuildEvidence result: {len(evidence_summary['proof_bullets'])} proof bullets"
    )
    
    return {
        "current_node": "build_evidence",
        "evidence_summary": evidence_summary,
        "trace_events": [trace_tool_call, trace_tool_result, trace_artifact]
    }


def create_build_evidence_node(services: Dict[str, Any]):
    """Create a build_evidence node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return build_evidence_node(state, services)
    return node_fn
