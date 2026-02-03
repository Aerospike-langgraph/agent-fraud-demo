"""
SelectCandidates Node - Choose top suspicious accounts from scored neighbors.

Ranks accounts by risk score and selects:
- High-risk candidates for fraud ring
- Evidence-based additions (shared infrastructure)
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.select_candidates")


def select_candidates_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select candidate accounts for fraud ring based on scores.
    
    Args:
        state: Current graph state
        services: Not used directly, but kept for consistency
        
    Returns:
        State updates with ranked_accounts
    """
    scores = state.get("scores", {})
    suspect_account_id = state["suspect_account_id"]
    
    logger.info(f"SelectCandidates: analyzing {len(scores)} scored accounts")
    
    # Rank accounts by score
    scored_items = [
        (account_id, score_info)
        for account_id, score_info in scores.items()
    ]
    
    # Sort by score descending
    scored_items.sort(key=lambda x: x[1].get("score", 0), reverse=True)
    
    # Extract ranked list
    ranked_accounts = [account_id for account_id, _ in scored_items]
    
    # Identify high-risk candidates
    high_risk_threshold = 0.6
    high_risk_accounts = [
        account_id for account_id, score_info in scored_items
        if score_info.get("score", 0) >= high_risk_threshold
    ]
    
    # Calculate metrics for decision making
    total_scored = len(scores)
    high_risk_count = len(high_risk_accounts)
    new_high_risk = len([
        acc for acc in high_risk_accounts 
        if acc not in state.get("fraud_ring_nodes", [])
    ])
    
    # Create trace event
    trace_event = {
        "type": "node_end",
        "node": "select_candidates",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "total_scored": total_scored,
            "high_risk_count": high_risk_count,
            "new_high_risk": new_high_risk,
            "top_candidates": [
                {"id": acc, "score": scores[acc].get("score", 0)}
                for acc in ranked_accounts[:5]
            ]
        }
    }
    
    logger.info(
        f"SelectCandidates result: {high_risk_count} high-risk, "
        f"{new_high_risk} new in this hop"
    )
    
    return {
        "current_node": "select_candidates",
        "ranked_accounts": ranked_accounts,
        "trace_events": [trace_event]
    }


def create_select_candidates_node(services: Dict[str, Any]):
    """Create a select_candidates node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return select_candidates_node(state, services)
    return node_fn
