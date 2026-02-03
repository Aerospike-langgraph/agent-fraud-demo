"""
FastAPI Application - Agentic Fraud Investigation API

Provides:
- REST endpoints for alerts and cases
- SSE streaming for real-time workflow progress
- Integration with LangGraph workflow
"""

# Apply nest_asyncio FIRST to allow nested event loops
# Required for gremlin-python which uses async internally
import nest_asyncio
nest_asyncio.apply()

import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import orjson

from services.aerospike_graph import AerospikeGraphService
from services.aerospike_db import AerospikeDBService
from tools.graph_tool import GraphTool
from tools.risk_scoring_tool import RiskScoringTool
from tools.evidence_tool import EvidenceTool
from tools.report_tool import ReportTool
from workflow.state import create_initial_state, GraphState
from workflow.graph import create_investigation_graph, get_workflow_visualization

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("agentic_fraud.api")

# Global services
graph_service: Optional[AerospikeGraphService] = None
db_service: Optional[AerospikeDBService] = None
services: Dict[str, Any] = {}

# Track running cases
running_cases: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup services."""
    global graph_service, db_service, services
    
    logger.info("Starting Agentic Fraud Investigation API...")
    
    # Initialize DB service (loads CSV data)
    db_service = AerospikeDBService(
        data_dir=os.environ.get(
            "DATA_DIR",
            "/Users/jnemade/Documents/Aerospike/data/synthetic_fraud_data"
        )
    )
    
    # Initialize Graph service
    graph_service = AerospikeGraphService(
        host=os.environ.get("GRAPH_HOST_ADDRESS", "localhost"),
        port=8182
    )
    
    try:
        graph_service.connect()
        logger.info("Connected to Aerospike Graph")
    except Exception as e:
        logger.warning(f"Could not connect to graph: {e}")
        logger.info("Graph operations will fail until connection is established")
    
    # Initialize tools
    graph_tool = GraphTool(graph_service)
    risk_scoring_tool = RiskScoringTool(graph_service)
    evidence_tool = EvidenceTool()
    report_tool = ReportTool(
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "mistral")
    )
    
    # Build services dict
    services = {
        "graph_service": graph_service,
        "db_service": db_service,
        "graph_tool": graph_tool,
        "risk_scoring_tool": risk_scoring_tool,
        "evidence_tool": evidence_tool,
        "report_tool": report_tool,
        "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "mistral")
    }
    
    logger.info("All services initialized")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Agentic Fraud Investigation API...")
    if graph_service:
        graph_service.close()


app = FastAPI(
    title="Agentic Fraud Investigation API",
    description="LangGraph-based fraud investigation with adaptive graph expansion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Agentic Fraud Investigation API",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    """Health check."""
    graph_status = "connected" if (graph_service and graph_service.client) else "disconnected"
    return {
        "status": "healthy",
        "graph_connection": graph_status,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# Alert Endpoints
# =============================================================================

@app.get("/api/alerts")
def get_alerts(
    status: Optional[str] = Query(None),
    risk_bucket: Optional[str] = Query(None),
    min_risk_score: Optional[float] = Query(None, ge=0, le=1),
    limit: Optional[int] = Query(50, ge=1, le=100)
):
    """Get all alerts with optional filtering."""
    if not db_service:
        raise HTTPException(status_code=503, detail="DB service not available")
    
    alerts = db_service.get_all_alerts(
        status=status,
        risk_bucket=risk_bucket,
        min_risk_score=min_risk_score,
        limit=limit
    )
    
    return {
        "alerts": alerts,
        "total": len(alerts)
    }


@app.get("/api/alerts/{alert_id}")
def get_alert(alert_id: str = Path(...)):
    """Get a specific alert."""
    if not db_service:
        raise HTTPException(status_code=503, detail="DB service not available")
    
    alert = db_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    return alert


# =============================================================================
# Case Endpoints
# =============================================================================

@app.post("/api/case/start")
def start_case(
    alert_id: str = Body(..., embed=True),
    max_hops: int = Body(3, embed=True),
    cost_budget: float = Body(1.0, embed=True),
    max_nodes: int = Body(80, embed=True)
):
    """Start a new investigation case."""
    if not db_service:
        raise HTTPException(status_code=503, detail="DB service not available")
    
    # Get alert
    alert = db_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    # Create case
    case_id = f"CASE_{uuid.uuid4().hex[:8].upper()}"
    suspect_account_id = alert.get("account_id")
    
    case = db_service.create_case(case_id, alert_id, suspect_account_id)
    
    # Initialize state
    initial_state = create_initial_state(
        case_id=case_id,
        alert_id=alert_id,
        suspect_account_id=suspect_account_id,
        max_hops_cap=max_hops,
        cost_budget=cost_budget,
        max_nodes=max_nodes
    )
    
    running_cases[case_id] = {
        "case": case,
        "state": initial_state,
        "events": [],
        "status": "created"
    }
    
    logger.info(f"Created case {case_id} for alert {alert_id}")
    
    return {
        "case_id": case_id,
        "alert_id": alert_id,
        "suspect_account_id": suspect_account_id,
        "status": "created"
    }


@app.get("/api/case/{case_id}")
def get_case(case_id: str = Path(...)):
    """Get case details and current state."""
    if case_id not in running_cases:
        if db_service:
            case = db_service.get_case(case_id)
            if case:
                return case
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    case_data = running_cases[case_id]
    state = case_data.get("state", {})
    
    # Debug: log raw counts
    raw_nodes = state.get("subgraph_nodes", [])
    raw_edges = state.get("subgraph_edges", [])
    logger.info(f"get_case {case_id}: raw state has {len(raw_nodes)} nodes, {len(raw_edges)} edges")
    
    # Deduplicate nodes and edges before returning
    nodes = raw_nodes
    edges = raw_edges
    
    # Dedupe nodes by ID, keeping the last occurrence (which has updated type)
    seen_node_ids = {}
    for node in nodes:
        seen_node_ids[node["id"]] = node
    unique_nodes = list(seen_node_ids.values())
    
    # Dedupe edges by source-target-type triple (keep different edge types)
    seen_edge_keys = {}
    for edge in edges:
        edge_type = edge.get("edge_type", "UNKNOWN")
        key = f"{edge['source']}->{edge['target']}:{edge_type}"
        seen_edge_keys[key] = edge
    unique_edges = list(seen_edge_keys.values())
    
    return {
        "case_id": case_id,
        "status": case_data.get("status", "unknown"),
        "workflow_status": case_data.get("status", "unknown"),
        "current_node": state.get("current_node", "unknown"),
        "current_hop": state.get("current_hop", 0),
        "estimated_cost": state.get("estimated_cost", 0),
        "nodes_explored": len(state.get("seen_nodes", [])),
        "fraud_ring_size": len(state.get("fraud_ring_nodes", [])),
        "fraud_ring_nodes": state.get("fraud_ring_nodes", []),
        "innocent_count": len(state.get("innocent_neighbors", [])),
        "subgraph": {
            "nodes": unique_nodes,
            "edges": unique_edges
        },
        "scores": state.get("scores", {}),
        "evidence_summary": state.get("evidence_summary", {}),
        "report_markdown": state.get("report_markdown", "")
    }


@app.post("/api/case/{case_id}/run")
async def run_case(case_id: str = Path(...)):
    """Start workflow execution for a case."""
    if case_id not in running_cases:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    case_data = running_cases[case_id]
    if case_data.get("status") == "running":
        raise HTTPException(status_code=400, detail="Case is already running")
    
    # Mark as running
    case_data["status"] = "running"
    
    # Run workflow in background
    asyncio.create_task(_run_workflow(case_id))
    
    return {
        "case_id": case_id,
        "status": "running",
        "message": "Workflow started. Use /api/case/{case_id}/stream to monitor progress."
    }


async def _run_workflow(case_id: str):
    """Execute the LangGraph workflow for a case."""
    case_data = running_cases.get(case_id)
    if not case_data:
        return
    
    logger.info(f"Starting workflow for case {case_id}")
    
    try:
        # Create the graph
        graph = create_investigation_graph(services)
        
        # Get initial state
        initial_state = case_data["state"]
        
        # Run the graph with streaming
        config = {"configurable": {"thread_id": case_id}}
        
        # Fields that should be accumulated (appended) instead of overwritten
        ACCUMULATING_FIELDS = {
            "seen_nodes", "seen_edges", "subgraph_nodes", "subgraph_edges",
            "trace_events", "decisions_history"
        }
        
        async for event in graph.astream(initial_state, config):
            # event is a dict with node name -> output
            for node_name, node_output in event.items():
                # Update state with proper accumulation
                if isinstance(node_output, dict):
                    for key, value in node_output.items():
                        if key in ACCUMULATING_FIELDS and isinstance(value, list):
                            # Append to existing list instead of overwriting
                            if key not in case_data["state"]:
                                case_data["state"][key] = []
                            case_data["state"][key].extend(value)
                        else:
                            # Overwrite for non-accumulating fields
                            case_data["state"][key] = value
                    
                    # Extract and store trace events
                    trace_events = node_output.get("trace_events", [])
                    case_data["events"].extend(trace_events)
                    
                    logger.info(f"Case {case_id}: completed node {node_name}")
        
        # Mark as completed
        case_data["status"] = "completed"
        logger.info(f"Workflow completed for case {case_id}")
        
    except Exception as e:
        logger.error(f"Workflow error for case {case_id}: {e}")
        case_data["status"] = "error"
        case_data["state"]["error_message"] = str(e)


@app.get("/api/case/{case_id}/stream")
async def stream_case(case_id: str = Path(...)):
    """SSE endpoint to stream workflow events."""
    if case_id not in running_cases:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        case_data = running_cases[case_id]
        last_event_index = 0
        
        while True:
            # Check for new events
            events = case_data.get("events", [])
            
            while last_event_index < len(events):
                event = events[last_event_index]
                last_event_index += 1
                
                yield {
                    "event": event.get("type", "update"),
                    "data": orjson.dumps(event).decode()
                }
            
            # Check if workflow is complete
            status = case_data.get("status", "")
            if status in ["completed", "error"]:
                # Send final state
                yield {
                    "event": "workflow_complete",
                    "data": orjson.dumps({
                        "status": status,
                        "case_id": case_id,
                        "final_state": {
                            "fraud_ring_size": len(case_data["state"].get("fraud_ring_nodes", [])),
                            "innocent_count": len(case_data["state"].get("innocent_neighbors", [])),
                            "total_hops": case_data["state"].get("current_hop", 0),
                            "total_cost": case_data["state"].get("estimated_cost", 0)
                        }
                    }).decode()
                }
                break
            
            await asyncio.sleep(0.1)
    
    return EventSourceResponse(event_generator())


# =============================================================================
# Workflow Visualization
# =============================================================================

@app.get("/api/workflow/structure")
def get_workflow_structure():
    """Get workflow structure for visualization."""
    return get_workflow_visualization()


# =============================================================================
# Graph Endpoints
# =============================================================================

@app.get("/api/graph/summary")
def get_graph_summary():
    """Get graph statistics."""
    if not graph_service or not graph_service.client:
        return {"error": "Graph not connected", "vertices": 0, "edges": 0}
    
    return graph_service.get_graph_summary()


@app.get("/api/manifest")
def get_manifest():
    """Get ground truth manifest."""
    if not db_service:
        raise HTTPException(status_code=503, detail="DB service not available")
    
    manifest = db_service.get_case_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    
    return manifest


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
