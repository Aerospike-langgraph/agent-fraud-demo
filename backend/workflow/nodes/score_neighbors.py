"""
ScoreNeighbors Node - Calculate risk scores for discovered accounts.

Calls the RiskScoringTool to:
- Score all newly discovered accounts
- Generate explainable risk reasons
- Update scores dictionary
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.score_neighbors")


def score_neighbors_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score discovered accounts using RiskScoringTool.
    
    Args:
        state: Current graph state
        services: Dict with risk_scoring_tool
        
    Returns:
        State updates with scores
    """
    risk_tool = services.get("risk_scoring_tool")
    
    suspect_account_id = state["suspect_account_id"]
    existing_scores = state.get("scores", {})
    subgraph_nodes = state.get("subgraph_nodes", [])
    
    # Get account IDs to score (exclude already scored)
    account_nodes = [
        n for n in subgraph_nodes 
        if n.get("label") == "account" and n["id"] not in existing_scores
    ]
    account_ids = [n["id"] for n in account_nodes]
    
    if not account_ids:
        logger.info("ScoreNeighbors: No new accounts to score")
        return {
            "current_node": "score_neighbors",
            "trace_events": [{
                "type": "node_end",
                "node": "score_neighbors",
                "timestamp": datetime.now().isoformat(),
                "data": {"accounts_scored": 0}
            }]
        }
    
    logger.info(f"ScoreNeighbors: scoring {len(account_ids)} accounts")
    
    # Create trace event for tool call
    trace_tool_call = {
        "type": "tool_call",
        "node": "score_neighbors",
        "tool": "score_accounts",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "account_count": len(account_ids),
            "accounts_sample": account_ids[:5]
        }
    }
    
    # Call risk scoring tool
    result = risk_tool.invoke(
        account_ids=account_ids,
        suspect_account_id=suspect_account_id,
        context={
            "current_hop": state["current_hop"],
            "subgraph_size": len(subgraph_nodes)
        }
    )
    
    # Update scores dictionary
    new_scores = {**existing_scores}
    for score_info in result.get("scores", []):
        account_id = score_info["account_id"]
        new_scores[account_id] = score_info
    
    # Create trace events
    summary = result.get("summary", {})
    trace_tool_result = {
        "type": "tool_result",
        "node": "score_neighbors",
        "tool": "score_accounts",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "total_scored": summary.get("total", 0),
            "high_risk": summary.get("high_risk_count", 0),
            "medium_risk": summary.get("medium_risk_count", 0),
            "low_risk": summary.get("low_risk_count", 0)
        }
    }
    
    # Score update event for UI
    trace_score_update = {
        "type": "score_update",
        "node": "score_neighbors",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "new_scores": [
                {"id": s["account_id"], "score": s["score"], "bucket": s["bucket"]}
                for s in result.get("scores", [])[:10]
            ],
            "summary": summary
        }
    }
    
    logger.info(
        f"ScoreNeighbors result: {summary.get('high_risk_count', 0)} high, "
        f"{summary.get('medium_risk_count', 0)} medium, "
        f"{summary.get('low_risk_count', 0)} low"
    )
    
    return {
        "current_node": "score_neighbors",
        "scores": new_scores,
        "trace_events": [trace_tool_call, trace_tool_result, trace_score_update]
    }


def create_score_neighbors_node(services: Dict[str, Any]):
    """Create a score_neighbors node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return score_neighbors_node(state, services)
    return node_fn
