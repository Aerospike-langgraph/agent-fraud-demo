"""
BuildSubgraph Node - Construct final fraud ring subgraph.

Takes the investigation results and builds:
- Final fraud ring with strong connections
- Innocent neighbors list
- Subgraph for visualization
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Set

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.build_subgraph")


def build_subgraph_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build final fraud ring subgraph from investigation results.
    
    Args:
        state: Current graph state
        services: Not used directly
        
    Returns:
        State updates with fraud_ring_nodes, innocent_neighbors
    """
    scores = state.get("scores", {})
    suspect_account_id = state["suspect_account_id"]
    subgraph_nodes = state.get("subgraph_nodes", [])
    subgraph_edges = state.get("subgraph_edges", [])
    
    logger.info(
        f"BuildSubgraph: analyzing {len(scores)} scored accounts, "
        f"{len(subgraph_nodes)} nodes, {len(subgraph_edges)} edges"
    )
    
    # Classify accounts
    fraud_ring_threshold = 0.8
    fraud_ring_accounts: Set[str] = {suspect_account_id}  # Always include suspect
    innocent_accounts: Set[str] = set()
    
    for account_id, score_info in scores.items():
        score = score_info.get("score", 0)
        if score >= fraud_ring_threshold:
            fraud_ring_accounts.add(account_id)
        else:
            innocent_accounts.add(account_id)
    
    # Filter edges to only those within the fraud ring
    fraud_ring_edges: List[str] = []
    for edge in subgraph_edges:
        source = edge.get("source", "")
        target = edge.get("target", "")
        
        # Include edge if both endpoints are in fraud ring OR
        # if one endpoint is a device/IP connected to a ring member
        source_in_ring = source in fraud_ring_accounts
        target_in_ring = target in fraud_ring_accounts
        
        # Also check if source/target is a device or IP
        source_is_infra = any(
            n["id"] == source and n["label"] in ["device", "ip"]
            for n in subgraph_nodes
        )
        target_is_infra = any(
            n["id"] == target and n["label"] in ["device", "ip"]
            for n in subgraph_nodes
        )
        
        # Include if: both in ring, or one in ring and other is infrastructure
        if (source_in_ring and target_in_ring) or \
           (source_in_ring and target_is_infra) or \
           (target_in_ring and source_is_infra):
            edge_id = f"{source}->{target}"
            fraud_ring_edges.append(edge_id)
    
    # Update node types in subgraph for visualization
    updated_nodes = []
    for node in subgraph_nodes:
        node_copy = dict(node)
        if node["id"] == suspect_account_id:
            node_copy["type"] = "suspect"
        elif node["id"] in fraud_ring_accounts:
            node_copy["type"] = "ring_candidate"
        elif node["id"] in innocent_accounts:
            node_copy["type"] = "innocent"
        elif node.get("label") in ["device", "ip"]:
            # Count how many FRAUD RING accounts are connected to this device/IP
            # Only mark as ring_infrastructure if connected to 2+ fraud accounts
            fraud_connections = 0
            for e in subgraph_edges:
                if e.get("source") == node["id"] or e.get("target") == node["id"]:
                    # Get the other end of the edge
                    other_id = e.get("target") if e.get("source") == node["id"] else e.get("source")
                    if other_id in fraud_ring_accounts:
                        fraud_connections += 1
            
            # Only mark as ring_infrastructure if shared by 2+ fraud accounts
            node_copy["type"] = "ring_infrastructure" if fraud_connections >= 2 else node.get("label", "background")
        updated_nodes.append(node_copy)
    
    # Create trace event
    trace_event = {
        "type": "node_end",
        "node": "build_subgraph",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "fraud_ring_size": len(fraud_ring_accounts),
            "innocent_count": len(innocent_accounts),
            "ring_edges": len(fraud_ring_edges),
            "fraud_ring_members": list(fraud_ring_accounts)[:10]
        }
    }
    
    # Artifact event for final subgraph
    trace_artifact = {
        "type": "artifact",
        "artifact_type": "subgraph_final",
        "node": "build_subgraph",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "ring_size": len(fraud_ring_accounts),
            "innocent_size": len(innocent_accounts)
        }
    }
    
    logger.info(
        f"BuildSubgraph result: {len(fraud_ring_accounts)} ring members, "
        f"{len(innocent_accounts)} innocents, {len(fraud_ring_edges)} ring edges"
    )
    
    return {
        "current_node": "build_subgraph",
        "fraud_ring_nodes": list(fraud_ring_accounts),
        "fraud_ring_edges": fraud_ring_edges,
        "innocent_neighbors": list(innocent_accounts),
        "subgraph_nodes": updated_nodes,
        "trace_events": [trace_event, trace_artifact]
    }


def create_build_subgraph_node(services: Dict[str, Any]):
    """Create a build_subgraph node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return build_subgraph_node(state, services)
    return node_fn
