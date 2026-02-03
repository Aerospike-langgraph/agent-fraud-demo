"""
DecideExpand Node - LLM-powered decision on whether to expand another hop.

This is the HYBRID node that uses Mistral/Ollama to reason about:
- Whether to continue expanding the graph
- Which edge types to prioritize next
- When the marginal value is dropping

The LLM receives context about current state and provides structured reasoning.

IMPORTANT: Hard caps are enforced BEFORE calling the LLM to prevent infinite loops.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

import httpx

from workflow.state import GraphState, ExpandDecision

logger = logging.getLogger("agentic_fraud.nodes.decide_expand")

# Hard limit to prevent infinite loops even if LLM keeps saying expand
ABSOLUTE_MAX_HOPS = 10


def decide_expand_node(state: GraphState, services: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decide whether to expand another hop using LLM reasoning.
    
    CRITICAL: Hard caps are checked FIRST before any LLM call.
    
    Args:
        state: Current graph state
        services: Dict with ollama_base_url, ollama_model
        
    Returns:
        State updates with expand_decision
    """
    ollama_base_url = services.get(
        "ollama_base_url", 
        os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model = services.get(
        "ollama_model",
        os.environ.get("OLLAMA_MODEL", "mistral")
    )
    
    # Gather context for decision
    current_hop = state["current_hop"]
    max_hops = state["max_hops_cap"]
    estimated_cost = state["estimated_cost"]
    cost_budget = state["cost_budget"]
    seen_nodes = state.get("seen_nodes", [])
    max_nodes = state["max_nodes"]
    scores = state.get("scores", {})
    frontier = state.get("frontier_accounts", [])
    
    # Calculate metrics
    high_risk_count = len([
        s for s in scores.values() 
        if s.get("bucket") in ["high", "critical"]
    ])
    
    logger.info(
        f"DecideExpand: hop={current_hop}/{max_hops}, "
        f"cost={estimated_cost:.2f}/{cost_budget}, "
        f"high_risk={high_risk_count}, frontier={len(frontier)}"
    )
    
    # =========================================================================
    # HARD CAPS - Only absolute safety valves, LLM decides everything else
    # =========================================================================
    hard_stop_reason = None
    
    # 1. Absolute maximum hops (safety valve only - very high)
    if current_hop >= ABSOLUTE_MAX_HOPS:
        hard_stop_reason = f"Absolute hop limit reached ({ABSOLUTE_MAX_HOPS})"
    
    # 2. No frontier accounts to explore (cannot continue anyway)
    elif len(frontier) == 0:
        hard_stop_reason = "No accounts in frontier to explore"
    
    # NOTE: Cost, max_hops, and node limits are now SOFT limits
    # The LLM sees these in context and decides whether to respect them
    
    # If hard stop triggered, skip LLM call entirely
    if hard_stop_reason:
        logger.info(f"DecideExpand HARD STOP: {hard_stop_reason}")
        decision = ExpandDecision(
            should_expand=False,
            next_edge_types=[],
            reason=hard_stop_reason,
            llm_reasoning=f"Hard stop triggered: {hard_stop_reason}"
        )
        
        trace_event = {
            "type": "decision",
            "node": "decide_expand",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "should_expand": False,
                "reason": hard_stop_reason,
                "hard_stop": True
            }
        }
        
        decision_record = {
            "hop": current_hop,
            "decision": False,
            "reason": hard_stop_reason,
            "hard_stop": True,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "current_node": "decide_expand",
            "expand_decision": decision,
            "decisions_history": [decision_record],
            "trace_events": [trace_event]
        }
    
    # =========================================================================
    # LLM Decision - Only called if no hard stops triggered
    # =========================================================================
    
    # Create trace event for LLM call
    trace_llm_call = {
        "type": "tool_call",
        "node": "decide_expand",
        "tool": "llm_reasoning",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "current_hop": current_hop,
            "max_hops": max_hops,
            "cost_used": estimated_cost,
            "cost_budget": cost_budget,
            "high_risk_found": high_risk_count,
            "frontier_size": len(frontier)
        }
    }
    
    # Build prompt for LLM
    context = _build_decision_context(state, scores)
    
    try:
        decision = _call_llm_for_decision(
            context, ollama_base_url, ollama_model
        )
    except Exception as e:
        logger.warning(f"LLM decision failed, using fallback: {e}")
        decision = _fallback_decision(state)
    
    # Create decision event for trace
    trace_decision = {
        "type": "decision",
        "node": "decide_expand",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "should_expand": decision["should_expand"],
            "next_edge_types": decision["next_edge_types"],
            "reason": decision["reason"],
            "llm_reasoning": decision["llm_reasoning"][:500] if decision.get("llm_reasoning") else ""
        }
    }
    
    # Record decision in history
    decision_record = {
        "hop": current_hop,
        "decision": decision["should_expand"],
        "reason": decision["reason"],
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(
        f"DecideExpand decision: expand={decision['should_expand']}, "
        f"reason={decision['reason']}"
    )
    
    return {
        "current_node": "decide_expand",
        "expand_decision": decision,
        "decisions_history": [decision_record],
        "trace_events": [trace_llm_call, trace_decision]
    }


def _build_decision_context(state: GraphState, scores: Dict) -> str:
    """Build context string for LLM prompt."""
    high_risk = [s for s in scores.values() if s.get("bucket") in ["high", "critical"]]
    medium_risk = [s for s in scores.values() if s.get("bucket") == "medium"]
    low_risk = [s for s in scores.values() if s.get("bucket") == "low"]
    
    # Count shared infrastructure
    shared_devices = 0
    shared_ips = 0
    for score_info in high_risk:
        evidence = score_info.get("evidence", {})
        shared_devices += evidence.get("shared_devices", 0)
        shared_ips += evidence.get("shared_ips", 0)
    
    frontier = state.get("frontier_accounts", [])
    
    context = f"""
FRAUD INVESTIGATION STATUS:

Exploration Progress:
- Hops completed: {state['current_hop']}
- Total accounts analyzed: {len(scores)}
- Frontier (accounts to explore next): {len(frontier)}

Fraud Ring Analysis:
- HIGH/CRITICAL risk accounts found: {len(high_risk)}
- Medium risk accounts: {len(medium_risk)}
- Low risk accounts: {len(low_risk)}
- Shared devices among high-risk: {shared_devices}
- Shared IPs among high-risk: {shared_ips}

Ring Completeness Assessment:
{"✓ Strong fraud ring detected (5+ high-risk)" if len(high_risk) >= 5 else "○ Still building fraud ring picture"}
{"✓ Good shared infrastructure" if (shared_devices > 0 or shared_ips > 0) else "○ Limited infrastructure sharing found"}
{"✓ Frontier exhausted" if len(frontier) == 0 else f"○ {len(frontier)} accounts still in frontier"}

Top Suspicious Accounts:
"""
    
    for score_info in sorted(high_risk, key=lambda x: x.get("score", 0), reverse=True)[:5]:
        reasons = score_info.get("reasons", [])
        reason_codes = [r.get("code", "") for r in reasons[:2]]
        evidence = score_info.get("evidence", {})
        context += f"- {score_info['account_id']}: score={score_info['score']:.2f}, shared_devices={evidence.get('shared_devices', 0)}, shared_ips={evidence.get('shared_ips', 0)}\n"
    
    if len(frontier) > 0:
        context += f"\nFrontier Preview (first 5): {frontier[:5]}\n"
    
    return context


def _call_llm_for_decision(
    context: str, 
    ollama_base_url: str, 
    ollama_model: str
) -> ExpandDecision:
    """Call Ollama/Mistral for expansion decision."""
    
    prompt = f"""You are an intelligent fraud investigation agent. Your goal is to identify fraud rings by exploring account connections.

{context}

You must decide: should we continue exploring more accounts, or have we found enough evidence?

DECISION GUIDELINES:
- CONTINUE expanding if:
  * We found high-risk accounts and there's a promising frontier to explore
  * We haven't yet built a complete picture of the fraud ring
  * The potential fraud ring might have more members to discover
  * Shared devices/IPs suggest more connected suspicious accounts

- STOP expanding if:
  * We've already identified a clear fraud ring (5+ connected high-risk accounts)
  * The frontier accounts are mostly low-risk (diminishing returns)
  * We've done 3+ hops and high-risk account discovery has slowed down
  * The fraud ring structure is complete (all high-risk accounts interconnected)

Provide your decision as JSON:
{{
    "should_expand": true/false,
    "next_edge_types": ["device", "ip", "tx"],
    "reason": "Brief decision reason",
    "reasoning": "Your analysis of the fraud ring completeness and whether more exploration would help"
}}

Respond ONLY with valid JSON."""

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{ollama_base_url}/api/chat",
            json={
                "model": ollama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a fraud investigation decision agent. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 500
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("message", {}).get("content", "{}")
        
        # Parse JSON from response
        try:
            # Clean up potential markdown formatting
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            
            return ExpandDecision(
                should_expand=parsed.get("should_expand", False),
                next_edge_types=parsed.get("next_edge_types", ["device", "ip", "tx"]),
                reason=parsed.get("reason", "LLM decision"),
                llm_reasoning=parsed.get("reasoning", content)
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response: {content[:200]}")
            raise


def _fallback_decision(state: GraphState) -> ExpandDecision:
    """Deterministic fallback decision when LLM fails - be exploratory."""
    current_hop = state["current_hop"]
    frontier = state.get("frontier_accounts", [])
    scores = state.get("scores", {})
    
    # Count high-risk accounts
    high_risk_count = len([
        s for s in scores.values() 
        if s.get("bucket") in ["high", "critical"]
    ])
    
    # Decision logic - be exploratory but not infinite
    should_expand = False
    reason = ""
    
    if len(frontier) == 0:
        reason = "No more accounts in frontier to explore"
    elif current_hop >= 5 and high_risk_count >= 5:
        # Good fraud ring found after reasonable exploration
        reason = f"Fraud ring identified: {high_risk_count} high-risk accounts after {current_hop} hops"
    elif current_hop >= 7:
        # Reasonable stopping point even without strong ring
        reason = f"Exploration complete: {current_hop} hops, {high_risk_count} high-risk accounts"
    elif len(frontier) > 0:
        should_expand = True
        reason = f"Continuing exploration: {len(frontier)} accounts in frontier, {high_risk_count} high-risk found"
    
    return ExpandDecision(
        should_expand=should_expand,
        next_edge_types=["device", "ip", "tx"] if should_expand else [],
        reason=reason,
        llm_reasoning=f"Fallback decision: {reason}"
    )


def create_decide_expand_node(services: Dict[str, Any]):
    """Create a decide_expand node function with services bound."""
    def node_fn(state: GraphState) -> Dict[str, Any]:
        return decide_expand_node(state, services)
    return node_fn


def should_continue_expansion(state: GraphState) -> str:
    """
    Conditional edge function for LangGraph routing.
    
    Returns:
        "traverse_graph" if should expand, "build_subgraph" otherwise
    """
    decision = state.get("expand_decision")
    if decision and decision.get("should_expand", False):
        return "traverse_graph"
    return "build_subgraph"
