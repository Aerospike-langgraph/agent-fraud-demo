"""
TraverseGraph Node - Expand graph from frontier accounts.

Calls the GraphTool to:
- Traverse through device/IP/transaction edges
- Discover new connected accounts
- Track traversal cost
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.traverse_graph")


def traverse_graph_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expand graph from frontier accounts using GraphTool.
    
    Args:
        state: Current graph state
        services: Dict with graph_tool
        
    Returns:
        State updates with new nodes, edges, frontier
    """
    graph_tool = services.get("graph_tool")
    
    frontier = state["frontier_accounts"]
    current_hop = state["current_hop"]
    seen_nodes = state.get("seen_nodes", [])
    max_nodes = state["max_nodes"]
    max_edges = state["max_edges"]
    
    # Determine edge types to expand (can be influenced by previous decisions)
    expand_decision = state.get("expand_decision")
    if expand_decision and expand_decision.get("next_edge_types"):
        edge_types = expand_decision["next_edge_types"]
    else:
        edge_types = ["device", "ip", "tx"]  # Default: all types
    
    logger.info(
        f"TraverseGraph: hop={current_hop + 1}, frontier={len(frontier)}, "
        f"edge_types={edge_types}"
    )
    
    # Create trace event for tool call
    trace_tool_call = {
        "type": "tool_call",
        "node": "traverse_graph",
        "tool": "expand_graph",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "seed_accounts": frontier[:5],  # Show first 5 in trace
            "seed_count": len(frontier),
            "edge_types": edge_types,
            "hop": current_hop + 1
        }
    }
    
    # Calculate remaining budget
    current_node_count = len(seen_nodes)
    remaining_node_budget = max(10, max_nodes - current_node_count)
    
    # Call graph tool
    result = graph_tool.invoke(
        seed_accounts=frontier,
        edge_types=edge_types,
        hop=current_hop + 1,
        node_limit=remaining_node_budget,
        edge_limit=max_edges,
        seen_nodes=seen_nodes
    )
    
    new_nodes = result.get("nodes", [])
    new_edges = result.get("edges", [])
    new_frontier = result.get("frontier_accounts", [])
    traversal_cost = result.get("estimated_cost", 0)
    
    # Create trace event for tool result
    trace_tool_result = {
        "type": "tool_result",
        "node": "traverse_graph",
        "tool": "expand_graph",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "nodes_found": len(new_nodes),
            "edges_found": len(new_edges),
            "new_frontier_size": len(new_frontier),
            "estimated_cost": traversal_cost,
            "success": result.get("success", True)
        }
    }
    
    # Graph update event for UI animation
    trace_graph_update = {
        "type": "graph_update",
        "node": "traverse_graph",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "added_nodes": [n["id"] for n in new_nodes[:20]],
            "added_edges": len(new_edges),
            "hop": current_hop + 1
        }
    }
    
    logger.info(
        f"TraverseGraph result: {len(new_nodes)} nodes, {len(new_edges)} edges, "
        f"cost={traversal_cost:.3f}"
    )
    
    # Extract new node IDs for seen_nodes
    new_node_ids = [n["id"] for n in new_nodes]
    new_edge_ids = [f"{e['source']}->{e['target']}" for e in new_edges]
    
    return {
        "current_node": "traverse_graph",
        "current_hop": current_hop + 1,
        "estimated_cost": state["estimated_cost"] + traversal_cost,
        "frontier_accounts": new_frontier,
        "subgraph_nodes": new_nodes,
        "subgraph_edges": new_edges,
        "seen_nodes": new_node_ids,
        "seen_edges": new_edge_ids,
        "trace_events": [trace_tool_call, trace_tool_result, trace_graph_update]
    }


def create_traverse_graph_node(services: Dict[str, Any]):
    """Create a traverse_graph node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return traverse_graph_node(state, services)
    return node_fn
