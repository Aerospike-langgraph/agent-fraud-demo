"""
Evidence Tool - Builds evidence summary from investigation results.

This tool is called by the BuildEvidenceSummary node to:
- Analyze the fraud subgraph for proof metrics
- Identify key shared infrastructure (devices, IPs)
- Generate explainable evidence bullets
"""

import logging
from typing import List, Dict, Any
from collections import Counter

logger = logging.getLogger("agentic_fraud.tools.evidence")


class EvidenceTool:
    """Tool for building evidence summaries."""
    
    name = "build_evidence"
    description = """
    Build evidence summary from fraud investigation results.
    Analyzes the discovered subgraph to identify:
    - Shared devices and IPs
    - Transaction patterns
    - Connection densities
    Returns structured evidence with proof bullets.
    """
    
    def invoke(
        self,
        fraud_ring_nodes: List[str],
        innocent_nodes: List[str],
        subgraph_nodes: List[Dict[str, Any]],
        subgraph_edges: List[Dict[str, Any]],
        scores: Dict[str, Dict[str, Any]],
        suspect_account_id: str
    ) -> Dict[str, Any]:
        """
        Build evidence summary from investigation data.
        
        Args:
            fraud_ring_nodes: Account IDs in the fraud ring
            innocent_nodes: Account IDs determined innocent
            subgraph_nodes: All discovered nodes
            subgraph_edges: All discovered edges
            scores: Risk scores by account ID
            suspect_account_id: The main suspect
            
        Returns:
            {
                "summary": High-level summary dict
                "proof_bullets": List of evidence points
                "shared_infrastructure": Details on shared devices/IPs
                "innocent_rationale": Why innocents were excluded
                "ring_connections": Connection patterns in the ring
            }
        """
        logger.info(
            f"EvidenceTool.invoke: {len(fraud_ring_nodes)} ring members, "
            f"{len(innocent_nodes)} innocents"
        )
        
        # Analyze shared infrastructure
        shared_devices = self._analyze_shared_devices(
            fraud_ring_nodes, subgraph_nodes, subgraph_edges
        )
        shared_ips = self._analyze_shared_ips(
            fraud_ring_nodes, subgraph_nodes, subgraph_edges
        )
        
        # Analyze transaction patterns
        tx_patterns = self._analyze_transactions(
            fraud_ring_nodes, subgraph_edges
        )
        
        # Build proof bullets
        proof_bullets = self._build_proof_bullets(
            fraud_ring_nodes, 
            shared_devices, 
            shared_ips, 
            tx_patterns,
            scores
        )
        
        # Build innocent rationale
        innocent_rationale = self._build_innocent_rationale(
            innocent_nodes, scores
        )
        
        # Calculate ring density
        ring_density = self._calculate_ring_density(
            fraud_ring_nodes, subgraph_edges
        )
        
        # Deduplicate counts for accurate metrics
        unique_nodes = {n.get("id") for n in subgraph_nodes if n.get("id")}
        unique_edges = {
            f"{e.get('source')}->{e.get('target')}:{e.get('edge_type', '')}" 
            for e in subgraph_edges
        }
        
        summary = {
            "ring_size": len(fraud_ring_nodes),
            "innocent_count": len(innocent_nodes),
            "total_nodes_explored": len(unique_nodes),
            "total_edges_explored": len(unique_edges),
            "shared_device_count": len(shared_devices.get("devices", [])),
            "shared_ip_count": len(shared_ips.get("ips", [])),
            "ring_density": ring_density,
            "avg_ring_score": self._calculate_avg_score(fraud_ring_nodes, scores),
            "avg_innocent_score": self._calculate_avg_score(innocent_nodes, scores)
        }
        
        logger.info(f"Evidence summary: {summary}")
        
        return {
            "summary": summary,
            "proof_bullets": proof_bullets,
            "shared_infrastructure": {
                "devices": shared_devices,
                "ips": shared_ips
            },
            "innocent_rationale": innocent_rationale,
            "ring_connections": tx_patterns,
            "success": True
        }
    
    def _analyze_shared_devices(
        self,
        ring_accounts: List[str],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """Find devices shared by ring members."""
        ring_set = set(ring_accounts)
        
        # Find all device nodes
        device_nodes = [n for n in nodes if n.get("label") == "device"]
        
        # Count how many ring accounts use each device
        device_usage = Counter()
        for edge in edges:
            if edge.get("edge_type") == "USES_DEVICE":
                source = edge.get("source", "")
                target = edge.get("target", "")
                
                # Find the device ID
                device_id = None
                account_id = None
                for node in device_nodes:
                    if node["id"] == source:
                        device_id = source
                        account_id = target
                    elif node["id"] == target:
                        device_id = target
                        account_id = source
                
                if device_id and account_id in ring_set:
                    device_usage[device_id] += 1
        
        # Get devices used by multiple ring members
        shared = [(d, c) for d, c in device_usage.items() if c >= 2]
        shared.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "devices": [{"id": d, "ring_users": c} for d, c in shared],
            "most_shared": shared[0] if shared else None
        }
    
    def _analyze_shared_ips(
        self,
        ring_accounts: List[str],
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """Find IPs shared by ring members."""
        ring_set = set(ring_accounts)
        
        # Find all IP nodes
        ip_nodes = [n for n in nodes if n.get("label") == "ip"]
        
        # Count how many ring accounts use each IP
        ip_usage = Counter()
        for edge in edges:
            if edge.get("edge_type") == "USES_IP":
                source = edge.get("source", "")
                target = edge.get("target", "")
                
                ip_id = None
                account_id = None
                for node in ip_nodes:
                    if node["id"] == source:
                        ip_id = source
                        account_id = target
                    elif node["id"] == target:
                        ip_id = target
                        account_id = source
                
                if ip_id and account_id in ring_set:
                    ip_usage[ip_id] += 1
        
        shared = [(ip, c) for ip, c in ip_usage.items() if c >= 2]
        shared.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "ips": [{"id": ip, "ring_users": c} for ip, c in shared],
            "most_shared": shared[0] if shared else None
        }
    
    def _analyze_transactions(
        self,
        ring_accounts: List[str],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze transaction patterns within the ring."""
        ring_set = set(ring_accounts)
        
        internal_tx = 0
        external_tx = 0
        
        for edge in edges:
            if edge.get("edge_type") == "TRANSACTS":
                source = edge.get("source", "")
                target = edge.get("target", "")
                
                if source in ring_set and target in ring_set:
                    internal_tx += 1
                elif source in ring_set or target in ring_set:
                    external_tx += 1
        
        return {
            "internal_transactions": internal_tx,
            "external_transactions": external_tx,
            "internal_ratio": internal_tx / max(internal_tx + external_tx, 1)
        }
    
    def _build_proof_bullets(
        self,
        ring_accounts: List[str],
        shared_devices: Dict,
        shared_ips: Dict,
        tx_patterns: Dict,
        scores: Dict
    ) -> List[str]:
        """Build human-readable proof points."""
        bullets = []
        
        # Ring size
        bullets.append(f"Identified fraud ring of {len(ring_accounts)} connected accounts")
        
        # Shared devices
        device_count = len(shared_devices.get("devices", []))
        if device_count > 0:
            most_shared = shared_devices.get("most_shared")
            if most_shared:
                bullets.append(
                    f"{device_count} device(s) shared among ring members; "
                    f"top device used by {most_shared[1]} accounts"
                )
        
        # Shared IPs
        ip_count = len(shared_ips.get("ips", []))
        if ip_count > 0:
            most_shared = shared_ips.get("most_shared")
            if most_shared:
                bullets.append(
                    f"{ip_count} IP address(es) shared among ring members; "
                    f"top IP used by {most_shared[1]} accounts"
                )
        
        # Transaction patterns
        if tx_patterns.get("internal_transactions", 0) > 0:
            bullets.append(
                f"{tx_patterns['internal_transactions']} internal transactions "
                f"between ring members ({tx_patterns['internal_ratio']:.0%} of ring activity)"
            )
        
        # High risk accounts
        high_risk = [
            acc for acc, score in scores.items()
            if score.get("bucket") in ["high", "critical"]
        ]
        if high_risk:
            bullets.append(f"{len(high_risk)} accounts classified as high/critical risk")
        
        return bullets
    
    def _build_innocent_rationale(
        self,
        innocent_accounts: List[str],
        scores: Dict
    ) -> List[Dict[str, Any]]:
        """Explain why innocent accounts were excluded."""
        rationale = []
        
        for account_id in innocent_accounts[:5]:  # Top 5
            score_info = scores.get(account_id, {})
            rationale.append({
                "account_id": account_id,
                "score": score_info.get("score", 0),
                "reason": "Low risk score; weak or no connections to ring infrastructure"
            })
        
        return rationale
    
    def _calculate_ring_density(
        self,
        ring_accounts: List[str],
        edges: List[Dict]
    ) -> float:
        """Calculate connection density within the ring."""
        n = len(ring_accounts)
        if n < 2:
            return 0.0
        
        ring_set = set(ring_accounts)
        internal_edges = 0
        
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source in ring_set and target in ring_set:
                internal_edges += 1
        
        max_edges = n * (n - 1) / 2  # Undirected
        return internal_edges / max_edges if max_edges > 0 else 0.0
    
    def _calculate_avg_score(
        self,
        account_ids: List[str],
        scores: Dict
    ) -> float:
        """Calculate average risk score for a set of accounts."""
        if not account_ids:
            return 0.0
        
        total = sum(
            scores.get(acc, {}).get("score", 0)
            for acc in account_ids
        )
        return round(total / len(account_ids), 3)


def create_evidence_tool() -> EvidenceTool:
    """Factory function to create EvidenceTool instance."""
    return EvidenceTool()
