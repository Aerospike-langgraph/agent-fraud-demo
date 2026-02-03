"""
LangGraph Definition - Fraud Investigation Workflow

Defines the StateGraph with:
- Nodes for each investigation step
- Conditional edges for expansion loop
- Checkpointing with Aerospike
"""

import logging
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from workflow.state import GraphState
from workflow.nodes.load_context import create_load_context_node
from workflow.nodes.traverse_graph import create_traverse_graph_node
from workflow.nodes.score_neighbors import create_score_neighbors_node
from workflow.nodes.select_candidates import create_select_candidates_node
from workflow.nodes.decide_expand import create_decide_expand_node, should_continue_expansion
from workflow.nodes.build_subgraph import create_build_subgraph_node
from workflow.nodes.build_evidence import create_build_evidence_node
from workflow.nodes.generate_report import create_generate_report_node

logger = logging.getLogger("agentic_fraud.workflow")


def create_investigation_graph(
    services: Dict[str, Any],
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Create the fraud investigation LangGraph workflow.
    
    The workflow follows this pattern:
    1. LoadContext - Initialize investigation
    2. TraverseGraph - Expand graph from frontier
    3. ScoreNeighbors - Score discovered accounts
    4. SelectCandidates - Choose high-risk candidates
    5. DecideExpand - LLM decides whether to continue
       - If yes: loop back to TraverseGraph
       - If no: proceed to BuildSubgraph
    6. BuildSubgraph - Construct final fraud ring
    7. BuildEvidence - Generate evidence summary
    8. GenerateReport - Create investigation report
    
    Args:
        services: Dict containing:
            - graph_service: AerospikeGraphService
            - db_service: AerospikeDBService
            - graph_tool: GraphTool
            - risk_scoring_tool: RiskScoringTool
            - evidence_tool: EvidenceTool
            - report_tool: ReportTool
            - ollama_base_url: Optional[str]
            - ollama_model: Optional[str]
        checkpointer: Optional checkpoint saver for persistence
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating fraud investigation graph...")
    
    # Create graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("load_context", create_load_context_node(services))
    workflow.add_node("traverse_graph", create_traverse_graph_node(services))
    workflow.add_node("score_neighbors", create_score_neighbors_node(services))
    workflow.add_node("select_candidates", create_select_candidates_node(services))
    workflow.add_node("decide_expand", create_decide_expand_node(services))
    workflow.add_node("build_subgraph", create_build_subgraph_node(services))
    workflow.add_node("build_evidence", create_build_evidence_node(services))
    workflow.add_node("generate_report", create_generate_report_node(services))
    
    # Set entry point
    workflow.set_entry_point("load_context")
    
    # Add edges - linear flow until decide_expand
    workflow.add_edge("load_context", "traverse_graph")
    workflow.add_edge("traverse_graph", "score_neighbors")
    workflow.add_edge("score_neighbors", "select_candidates")
    workflow.add_edge("select_candidates", "decide_expand")
    
    # Conditional edge from decide_expand
    # If should_expand: loop back to traverse_graph
    # If not: proceed to build_subgraph
    workflow.add_conditional_edges(
        "decide_expand",
        should_continue_expansion,
        {
            "traverse_graph": "traverse_graph",
            "build_subgraph": "build_subgraph"
        }
    )
    
    # Continue linear flow after expansion loop ends
    workflow.add_edge("build_subgraph", "build_evidence")
    workflow.add_edge("build_evidence", "generate_report")
    workflow.add_edge("generate_report", END)
    
    # Compile with optional checkpointer
    if checkpointer:
        logger.info("Compiling graph with Aerospike checkpointer")
        compiled = workflow.compile(checkpointer=checkpointer)
    else:
        logger.info("Compiling graph without checkpointer")
        compiled = workflow.compile()
    
    logger.info("Fraud investigation graph created successfully")
    return compiled


def get_workflow_visualization():
    """
    Return a description of the workflow for documentation.
    
    Returns:
        Dict with workflow structure
    """
    return {
        "nodes": [
            {"id": "load_context", "label": "Load Context", "description": "Initialize investigation with alert data"},
            {"id": "traverse_graph", "label": "Traverse Graph", "description": "Expand graph from frontier accounts"},
            {"id": "score_neighbors", "label": "Score Neighbors", "description": "Calculate risk scores for discovered accounts"},
            {"id": "select_candidates", "label": "Select Candidates", "description": "Choose high-risk candidates"},
            {"id": "decide_expand", "label": "Decide Expand", "description": "LLM decides whether to continue expansion"},
            {"id": "build_subgraph", "label": "Build Subgraph", "description": "Construct final fraud ring"},
            {"id": "build_evidence", "label": "Build Evidence", "description": "Generate evidence summary"},
            {"id": "generate_report", "label": "Generate Report", "description": "Create investigation report"}
        ],
        "edges": [
            {"from": "load_context", "to": "traverse_graph"},
            {"from": "traverse_graph", "to": "score_neighbors"},
            {"from": "score_neighbors", "to": "select_candidates"},
            {"from": "select_candidates", "to": "decide_expand"},
            {"from": "decide_expand", "to": "traverse_graph", "condition": "should_expand=true"},
            {"from": "decide_expand", "to": "build_subgraph", "condition": "should_expand=false"},
            {"from": "build_subgraph", "to": "build_evidence"},
            {"from": "build_evidence", "to": "generate_report"},
            {"from": "generate_report", "to": "END"}
        ]
    }
