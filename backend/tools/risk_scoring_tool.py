"""
Risk Scoring Tool - Calculates fraud risk scores for accounts.

This tool is called by the ScoreNeighbors node to:
- Calculate risk scores based on graph features
- Generate explainable risk reasons
- Classify accounts into risk buckets
"""

import logging
from typing import List, Dict, Any
import math

from services.aerospike_graph import AerospikeGraphService
from workflow.state import AccountScore

logger = logging.getLogger("agentic_fraud.tools.risk")


class RiskScoringTool:
    """Tool for calculating fraud risk scores."""
    
    name = "score_accounts"
    description = """
    Calculate fraud risk scores for a list of accounts.
    Uses graph-based features like shared devices, shared IPs, 
    transaction patterns, and historical indicators.
    Returns scores with explainable reasons.
    """
    
    def __init__(self, graph_service: AerospikeGraphService):
        self.graph_service = graph_service
    
    def invoke(
        self,
        account_ids: List[str],
        suspect_account_id: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Score multiple accounts for fraud risk.
        
        Args:
            account_ids: Accounts to score
            suspect_account_id: The main suspect (for context)
            context: Additional context (subgraph info, etc.)
            
        Returns:
            {
                "scores": List[AccountScore]
                "summary": {high_risk_count, medium_risk_count, low_risk_count}
                "success": bool
            }
        """
        logger.info(f"RiskScoringTool.invoke: scoring {len(account_ids)} accounts")
        
        context = context or {}
        scores = []
        
        for account_id in account_ids:
            try:
                score_result = self._score_single_account(
                    account_id, 
                    suspect_account_id,
                    context
                )
                scores.append(score_result)
            except Exception as e:
                logger.error(f"Error scoring {account_id}: {e}")
                # Add a default low score for failed accounts
                scores.append({
                    "account_id": account_id,
                    "score": 0.1,
                    "bucket": "low",
                    "reasons": [{"code": "SCORING_ERROR", "weight": 0, "description": str(e)}],
                    "evidence": {}
                })
        
        # Calculate summary
        high_count = len([s for s in scores if s["bucket"] in ["high", "critical"]])
        medium_count = len([s for s in scores if s["bucket"] == "medium"])
        low_count = len([s for s in scores if s["bucket"] == "low"])
        
        logger.info(
            f"Scoring complete: {high_count} high, {medium_count} medium, {low_count} low"
        )
        
        return {
            "scores": scores,
            "summary": {
                "high_risk_count": high_count,
                "medium_risk_count": medium_count,
                "low_risk_count": low_count,
                "total": len(scores)
            },
            "success": True
        }
    
    def _score_single_account(
        self,
        account_id: str,
        suspect_account_id: str,
        context: Dict[str, Any]
    ) -> AccountScore:
        """Calculate risk score for a single account."""
        
        # Get graph features
        features = self.graph_service.get_account_features(account_id)
        
        # Initialize scoring components
        score = 0.0
        reasons = []
        evidence = {
            "shared_devices": features.get("shared_device_accounts", 0),
            "shared_ips": features.get("shared_ip_accounts", 0),
            "transaction_count": features.get("transaction_count", 0),
            "is_vpn_user": features.get("is_vpn_user", False),
            "is_emulator_user": features.get("is_emulator_user", False)
        }
        
        # 1. Shared device score (0-35 points)
        shared_devices = features.get("shared_device_accounts", 0)
        if shared_devices > 0:
            device_score = min(shared_devices / 10.0, 1.0) * 35
            score += device_score
            if shared_devices >= 3:
                reasons.append({
                    "code": "SHARED_DEVICES",
                    "weight": device_score,
                    "description": f"Shares devices with {shared_devices} other accounts"
                })
        
        # 2. Shared IP score (0-25 points)
        shared_ips = features.get("shared_ip_accounts", 0)
        if shared_ips > 0:
            ip_score = min(shared_ips / 15.0, 1.0) * 25
            score += ip_score
            if shared_ips >= 5:
                reasons.append({
                    "code": "SHARED_IPS",
                    "weight": ip_score,
                    "description": f"Shares IP addresses with {shared_ips} other accounts"
                })
        
        # 3. VPN usage (0-15 points)
        if features.get("is_vpn_user", False):
            vpn_score = 15
            score += vpn_score
            reasons.append({
                "code": "VPN_USAGE",
                "weight": vpn_score,
                "description": "Uses VPN/proxy IP addresses"
            })
        
        # 4. Emulator usage (0-15 points)
        if features.get("is_emulator_user", False):
            emulator_score = 15
            score += emulator_score
            reasons.append({
                "code": "EMULATOR_USAGE",
                "weight": emulator_score,
                "description": "Uses emulator or automation tools"
            })
        
        # 5. Transaction velocity (0-10 points)
        tx_count = features.get("transaction_count", 0)
        if tx_count > 20:
            velocity_score = min((tx_count - 20) / 30.0, 1.0) * 10
            score += velocity_score
            reasons.append({
                "code": "HIGH_TX_VELOCITY",
                "weight": velocity_score,
                "description": f"High transaction count: {tx_count}"
            })
        
        # Normalize score to 0-1
        normalized_score = min(score / 100.0, 1.0)
        
        # Determine bucket
        if normalized_score >= 0.8:
            bucket = "critical"
        elif normalized_score >= 0.8:
            bucket = "high"
        elif normalized_score >= 0.4:
            bucket = "medium"
        else:
            bucket = "low"
        
        # If no specific reasons, add a default
        if not reasons:
            reasons.append({
                "code": "LOW_RISK",
                "weight": 0,
                "description": "No significant risk indicators detected"
            })
        
        return AccountScore(
            account_id=account_id,
            score=round(normalized_score, 3),
            bucket=bucket,
            reasons=reasons,
            evidence=evidence
        )


def create_risk_scoring_tool(graph_service: AerospikeGraphService) -> RiskScoringTool:
    """Factory function to create RiskScoringTool instance."""
    return RiskScoringTool(graph_service)
