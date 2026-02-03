"""
Graph Tool - Traverses Aerospike Graph to expand fraud investigation.

This tool is called by the TraverseGraph node to:
- Expand from seed accounts through device/IP/transaction edges
- Track cost estimates for adaptive stopping
- Return new nodes and frontier accounts for next expansion
"""

import logging
from typing import List, Dict, Any, Set

from services.aerospike_graph import AerospikeGraphService

logger = logging.getLogger("agentic_fraud.tools.graph")


class GraphTool:
    """Tool for graph traversal in fraud investigation."""
    
    name = "expand_graph"
    description = """
    Expand the fraud investigation graph from seed accounts.
    Traverses through device, IP, and transaction relationships to find connected accounts.
    Returns new nodes, edges, frontier accounts, and estimated traversal cost.
    """
    
    def __init__(self, graph_service: AerospikeGraphService):
        self.graph_service = graph_service
    
    def invoke(
        self,
        seed_accounts: List[str],
        edge_types: List[str],
        hop: int,
        node_limit: int,
        edge_limit: int,
        seen_nodes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute graph expansion.
        
        Args:
            seed_accounts: Account IDs to expand from
            edge_types: Types to traverse: ["device", "ip", "tx"]
            hop: Current hop number
            node_limit: Max new nodes to return
            edge_limit: Max new edges to return
            seen_nodes: Already visited node IDs
            
        Returns:
            {
                "nodes": List of new node objects
                "edges": List of new edge objects
                "frontier_accounts": New accounts discovered
                "estimated_cost": Cost of this traversal
                "hop": Hop number
                "success": bool
                "error": Optional error message
            }
        """
        logger.info(
            f"GraphTool.invoke: hop={hop}, seeds={len(seed_accounts)}, "
            f"edge_types={edge_types}, limits=({node_limit}, {edge_limit})"
        )
        
        try:
            result = self.graph_service.expand_graph(
                seed_accounts=seed_accounts,
                edge_types=edge_types,
                hop=hop,
                node_limit=node_limit,
                edge_limit=edge_limit,
                seen_nodes=set(seen_nodes or [])
            )
            
            result["success"] = True
            result["error"] = None
            
            logger.info(
                f"GraphTool result: {len(result['nodes'])} nodes, "
                f"{len(result['edges'])} edges, "
                f"{len(result['frontier_accounts'])} frontier accounts, "
                f"cost={result['estimated_cost']:.3f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"GraphTool error: {e}")
            return {
                "nodes": [],
                "edges": [],
                "frontier_accounts": [],
                "estimated_cost": 0.0,
                "hop": hop,
                "success": False,
                "error": str(e)
            }
    
    def get_account_features(self, account_id: str) -> Dict[str, Any]:
        """Get graph-based features for a single account."""
        try:
            return self.graph_service.get_account_features(account_id)
        except Exception as e:
            logger.error(f"Error getting features for {account_id}: {e}")
            return {}


def create_graph_tool(graph_service: AerospikeGraphService) -> GraphTool:
    """Factory function to create GraphTool instance."""
    return GraphTool(graph_service)
