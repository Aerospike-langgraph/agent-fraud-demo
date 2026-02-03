"""
GenerateReport Node - Generate investigation report using ReportTool.

Uses Mistral/Ollama to generate:
- Professional markdown report
- Executive summary
- Recommendations
"""

import logging
from datetime import datetime
from typing import Dict, Any

from workflow.state import GraphState

logger = logging.getLogger("agentic_fraud.nodes.generate_report")


def generate_report_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate investigation report using ReportTool.
    
    Args:
        state: Current graph state
        services: Dict with report_tool
        
    Returns:
        State updates with report_markdown
    """
    report_tool = services.get("report_tool")
    
    case_id = state["case_id"]
    suspect_account_id = state["suspect_account_id"]
    fraud_ring_nodes = state.get("fraud_ring_nodes", [])
    innocent_nodes = state.get("innocent_neighbors", [])
    evidence_summary = state.get("evidence_summary", {})
    scores = state.get("scores", {})
    
    logger.info(f"GenerateReport: generating report for case {case_id}")
    
    # Create trace event for tool call
    trace_tool_call = {
        "type": "tool_call",
        "node": "generate_report",
        "tool": "generate_report",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "case_id": case_id,
            "ring_size": len(fraud_ring_nodes)
        }
    }
    
    # Call report tool
    result = report_tool.invoke(
        case_id=case_id,
        suspect_account_id=suspect_account_id,
        fraud_ring_nodes=fraud_ring_nodes,
        innocent_nodes=innocent_nodes,
        evidence_summary=evidence_summary,
        scores=scores
    )
    
    report_markdown = result.get("report_markdown", "")
    generation_method = result.get("generation_method", "unknown")
    
    # Create trace events
    trace_tool_result = {
        "type": "tool_result",
        "node": "generate_report",
        "tool": "generate_report",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "report_length": len(report_markdown),
            "generation_method": generation_method,
            "success": result.get("success", False)
        }
    }
    
    trace_artifact = {
        "type": "artifact",
        "artifact_type": "report",
        "node": "generate_report",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "length": len(report_markdown),
            "method": generation_method
        }
    }
    
    logger.info(
        f"GenerateReport result: {len(report_markdown)} chars, "
        f"method={generation_method}"
    )
    
    return {
        "current_node": "generate_report",
        "report_markdown": report_markdown,
        "workflow_status": "completed",
        "trace_events": [trace_tool_call, trace_tool_result, trace_artifact]
    }


def create_generate_report_node(services: Dict[str, Any]):
    """Create a generate_report node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return generate_report_node(state, services)
    return node_fn
