"""
LoadContext Node - Initialize investigation with alert and suspect data.

First node in the LangGraph workflow. Loads:
- Alert details
- Suspect account profile
- Initializes traversal budgets and frontier
"""

import logging
from datetime import datetime
from typing import Dict, Any

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.load_context")


def load_context_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load case context and initialize investigation.
    
    Args:
        state: Current graph state
        services: Dict with db_service, graph_service
        
    Returns:
        State updates
    """
    db_service = services.get("db_service")
    
    alert_id = state["alert_id"]
    suspect_account_id = state["suspect_account_id"]
    
    logger.info(f"LoadContext: alert={alert_id}, suspect={suspect_account_id}")
    
    # Create trace event
    trace_event = {
        "type": "node_start",
        "node": "load_context",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "alert_id": alert_id,
            "suspect_account_id": suspect_account_id
        }
    }
    
    # Load alert details
    alert = None
    if db_service:
        alert = db_service.get_alert_by_id(alert_id)
        if not alert:
            alert = db_service.get_alert_by_account_id(suspect_account_id)
    
    # Load account data
    account_data = None
    if db_service:
        account_data = db_service.get_account_data(suspect_account_id)
    
    # Create suspect node
    suspect_node = {
        "id": suspect_account_id,
        "label": "account",
        "type": "suspect",
        "properties": {
            "account_id": suspect_account_id,
            "risk_score": alert.get("risk_score", 0.9) if alert else 0.9,
            "risk_bucket": alert.get("risk_bucket", "high") if alert else "high",
            "reason": alert.get("reason", "High-risk alert") if alert else "Investigation target",
            **(account_data or {})
        }
    }
    
    # Complete trace event
    trace_complete = {
        "type": "node_end",
        "node": "load_context",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "alert_loaded": alert is not None,
            "account_loaded": account_data is not None,
            "frontier_size": 1
        }
    }
    
    logger.info(
        f"LoadContext complete: alert_loaded={alert is not None}, "
        f"account_loaded={account_data is not None}"
    )
    
    return {
        "current_node": "load_context",
        "frontier_accounts": [suspect_account_id],
        "subgraph_nodes": [suspect_node],
        "seen_nodes": [suspect_account_id],
        "trace_events": [trace_event, trace_complete]
    }


def create_load_context_node(services: Dict[str, Any]):
    """Create a load_context node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return load_context_node(state, services)
    return node_fn
