"""
Aerospike Graph Service - Gremlin-based graph traversal for fraud investigation.

Provides methods for:
- Expanding accounts through device/IP/transaction edges
- Getting account neighbors and connection patterns
- Calculating graph-based features for risk scoring
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T, P

logger = logging.getLogger("agentic_fraud.graph")


class AerospikeGraphService:
    """Service for interacting with Aerospike Graph via Gremlin."""
    
    def __init__(
        self,
        host: str = None,
        port: int = 8182
    ):
        self.host = host or os.environ.get("GRAPH_HOST_ADDRESS", "localhost")
        self.port = port
        self.client = None
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection to Aerospike Graph."""
        try:
            url = f"ws://{self.host}:{self.port}/gremlin"
            logger.info(f"Connecting to Aerospike Graph: {url}")
            
            # Use simple synchronous connection
            self.connection = DriverRemoteConnection(url, "g")
            self.client = traversal().with_remote(self.connection)
            
            # Test connection
            test_result = self.client.inject(0).next()
            if test_result != 0:
                raise Exception("Connection test failed")
            
            logger.info("Connected to Aerospike Graph Service")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Aerospike Graph: {e}")
            self.client = None
            self.connection = None
            raise
    
    def close(self):
        """Close graph connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Disconnected from Aerospike Graph")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
    
    def expand_graph(
        self,
        seed_accounts: List[str],
        edge_types: List[str],
        hop: int,
        node_limit: int,
        edge_limit: int,
        seen_nodes: Set[str] = None
    ) -> Dict[str, Any]:
        """
        Expand graph from seed accounts through specified edge types.
        
        This is the main Graph Tool used by the LangGraph workflow.
        
        Args:
            seed_accounts: Account IDs to expand from
            edge_types: Types of edges to traverse ["device", "ip", "tx"]
            hop: Current hop number (for tracking)
            node_limit: Maximum new nodes to return
            edge_limit: Maximum new edges to return
            seen_nodes: Set of already-visited node IDs to skip
            
        Returns:
            {
                "nodes": [NodeInfo],
                "edges": [EdgeInfo],
                "frontier_accounts": [str],  # New accounts discovered
                "estimated_cost": float
            }
        """
        if not self.client:
            raise Exception("Graph client not connected")
        
        logger.info(f"expand_graph: seeds={len(seed_accounts)}, edge_types={edge_types}, limit={node_limit}")
        
        # Quick connectivity test
        try:
            test = self.client.inject(1).next()
            logger.info(f"expand_graph: connection test passed (result={test})")
        except Exception as e:
            logger.error(f"expand_graph: connection test FAILED: {e}")
            raise
        
        seen_nodes = seen_nodes or set()
        new_nodes = []
        new_edges = []
        frontier_accounts = set()
        
        for account_id in seed_accounts:
            if len(new_nodes) >= node_limit:
                break
            
            # Expand through devices
            if "device" in edge_types:
                device_results = self._expand_via_devices(
                    account_id, seen_nodes, node_limit - len(new_nodes)
                )
                new_nodes.extend(device_results["nodes"])
                new_edges.extend(device_results["edges"])
                frontier_accounts.update(device_results["connected_accounts"])
            
            # Expand through IPs
            if "ip" in edge_types:
                ip_results = self._expand_via_ips(
                    account_id, seen_nodes, node_limit - len(new_nodes)
                )
                new_nodes.extend(ip_results["nodes"])
                new_edges.extend(ip_results["edges"])
                frontier_accounts.update(ip_results["connected_accounts"])
            
            # Expand through transactions
            if "tx" in edge_types:
                tx_results = self._expand_via_transactions(
                    account_id, seen_nodes, node_limit - len(new_nodes)
                )
                new_nodes.extend(tx_results["nodes"])
                new_edges.extend(tx_results["edges"])
                frontier_accounts.update(tx_results["connected_accounts"])
        
        # Remove seed accounts from frontier
        frontier_accounts -= set(seed_accounts)
        frontier_accounts -= seen_nodes
        
        # Calculate estimated cost (proportional to data retrieved)
        estimated_cost = (len(new_nodes) / 100.0) + (len(new_edges) / 200.0)
        
        return {
            "nodes": new_nodes[:node_limit],
            "edges": new_edges[:edge_limit],
            "frontier_accounts": list(frontier_accounts),
            "estimated_cost": estimated_cost,
            "hop": hop
        }
    
    def _expand_via_devices(
        self,
        account_id: str,
        seen_nodes: Set[str],
        limit: int
    ) -> Dict[str, Any]:
        """Find accounts connected through shared devices."""
        nodes = []
        edges = []
        connected_accounts = set()
        
        try:
            logger.info(f"_expand_via_devices: starting for {account_id}")
            
            # Single optimized query: account -> devices -> other accounts
            # Returns paths with device and account info in one roundtrip
            results = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_DEVICE")
                .limit(10)  # Limit devices to avoid explosion
                .as_("device")
                .in_("USES_DEVICE")
                .has_label("account")
                .limit(limit)
                .as_("other_account")
                .select("device", "other_account")
                .by(__.element_map())
                .by(__.element_map())
                .to_list()
            )
            logger.info(f"_expand_via_devices: found {len(results)} device-account pairs")
            
            seen_devices = set()
            for result in results:
                device_map = result.get("device", {})
                other_map = result.get("other_account", {})
                
                device_props = self._extract_props_from_map(device_map)
                device_id = device_props.get("device_id", str(device_map.get(T.id, "")))
                
                other_props = self._extract_props_from_map(other_map)
                other_account_id = other_props.get("account_id", str(other_map.get(T.id, "")))
                
                # Add device node if not seen
                if device_id not in seen_nodes and device_id not in seen_devices:
                    nodes.append({
                        "id": device_id,
                        "label": "device",
                        "type": "device",
                        "properties": device_props
                    })
                    seen_devices.add(device_id)
                    edges.append({
                        "source": account_id,
                        "target": device_id,
                        "edge_type": "USES_DEVICE",
                        "properties": {}
                    })
                
                # Add connected account if not the same as source
                if other_account_id != account_id and other_account_id not in seen_nodes:
                    nodes.append({
                        "id": other_account_id,
                        "label": "account",
                        "type": "connected",
                        "properties": other_props
                    })
                    connected_accounts.add(other_account_id)
                    edges.append({
                        "source": device_id,
                        "target": other_account_id,
                        "edge_type": "USES_DEVICE",
                        "properties": {}
                    })
                
                if len(nodes) >= limit:
                    break
                    
        except Exception as e:
            logger.error(f"Error expanding via devices for {account_id}: {e}")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "connected_accounts": connected_accounts
        }
    
    def _expand_via_ips(
        self,
        account_id: str,
        seen_nodes: Set[str],
        limit: int
    ) -> Dict[str, Any]:
        """Find accounts connected through shared IPs."""
        nodes = []
        edges = []
        connected_accounts = set()
        
        try:
            logger.info(f"_expand_via_ips: starting for {account_id}")
            
            # Single optimized query: account -> IPs -> other accounts
            results = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_IP")
                .limit(10)  # Limit IPs to avoid explosion
                .as_("ip")
                .in_("USES_IP")
                .has_label("account")
                .limit(limit)
                .as_("other_account")
                .select("ip", "other_account")
                .by(__.element_map())
                .by(__.element_map())
                .to_list()
            )
            logger.info(f"_expand_via_ips: found {len(results)} ip-account pairs")
            
            seen_ips = set()
            for result in results:
                ip_map = result.get("ip", {})
                other_map = result.get("other_account", {})
                
                ip_props = self._extract_props_from_map(ip_map)
                ip_id = ip_props.get("ip_id", str(ip_map.get(T.id, "")))
                
                other_props = self._extract_props_from_map(other_map)
                other_account_id = other_props.get("account_id", str(other_map.get(T.id, "")))
                
                # Add IP node if not seen
                if ip_id not in seen_nodes and ip_id not in seen_ips:
                    nodes.append({
                        "id": ip_id,
                        "label": "ip",
                        "type": "ip",
                        "properties": ip_props
                    })
                    seen_ips.add(ip_id)
                    edges.append({
                        "source": account_id,
                        "target": ip_id,
                        "edge_type": "USES_IP",
                        "properties": {}
                    })
                
                # Add connected account if not the same as source
                if other_account_id != account_id and other_account_id not in seen_nodes:
                    nodes.append({
                        "id": other_account_id,
                        "label": "account",
                        "type": "connected",
                        "properties": other_props
                    })
                    connected_accounts.add(other_account_id)
                    edges.append({
                        "source": ip_id,
                        "target": other_account_id,
                        "edge_type": "USES_IP",
                        "properties": {}
                    })
                
                if len(nodes) >= limit:
                    break
                    
        except Exception as e:
            logger.error(f"Error expanding via IPs for {account_id}: {e}")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "connected_accounts": connected_accounts
        }
    
    def _expand_via_transactions(
        self,
        account_id: str,
        seen_nodes: Set[str],
        limit: int
    ) -> Dict[str, Any]:
        """Find accounts connected through transactions."""
        nodes = []
        edges = []
        connected_accounts = set()
        
        try:
            logger.info(f"_expand_via_transactions: starting for {account_id}")
            # Get all connected accounts via TRANSACTS in a single query with properties
            tx_partner_maps = (
                self.client.V()
                .has("account", "account_id", account_id)
                .both("TRANSACTS")
                .has_label("account")
                .dedup()
                .limit(limit)
                .element_map()
                .to_list()
            )
            logger.info(f"_expand_via_transactions: found {len(tx_partner_maps)} partners")
            
            for other_map in tx_partner_maps:
                other_props = self._extract_props_from_map(other_map)
                other_account_id = other_props.get("account_id", str(other_map.get(T.id, "")))
                
                if other_account_id != account_id and other_account_id not in seen_nodes:
                    nodes.append({
                        "id": other_account_id,
                        "label": "account",
                        "type": "connected",
                        "properties": other_props
                    })
                    connected_accounts.add(other_account_id)
                    
                    edges.append({
                        "source": account_id,
                        "target": other_account_id,
                        "edge_type": "TRANSACTS",
                        "properties": {}
                    })
                    
        except Exception as e:
            logger.error(f"Error expanding via transactions for {account_id}: {e}")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "connected_accounts": connected_accounts
        }
    
    def get_account_features(self, account_id: str) -> Dict[str, Any]:
        """Get graph-based features for an account (for risk scoring)."""
        if not self.client:
            raise Exception("Graph client not connected")
        
        features = {
            "device_count": 0,
            "ip_count": 0,
            "transaction_count": 0,
            "shared_device_accounts": 0,
            "shared_ip_accounts": 0,
            "max_device_sharing": 0,
            "max_ip_sharing": 0,
            "is_vpn_user": False,
            "is_emulator_user": False
        }
        
        try:
            # Count devices (lookup by account_id property)
            features["device_count"] = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_DEVICE")
                .count()
                .next()
            )
            
            # Count IPs
            features["ip_count"] = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_IP")
                .count()
                .next()
            )
            
            # Count transactions
            features["transaction_count"] = (
                self.client.V()
                .has("account", "account_id", account_id)
                .bothE("TRANSACTS")
                .count()
                .next()
            )
            
            # Count accounts sharing devices
            shared_device_accounts = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_DEVICE")
                .in_("USES_DEVICE")
                .has_label("account")
                .dedup()
                .count()
                .next()
            )
            features["shared_device_accounts"] = max(0, shared_device_accounts - 1)
            
            # Count accounts sharing IPs
            shared_ip_accounts = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_IP")
                .in_("USES_IP")
                .has_label("account")
                .dedup()
                .count()
                .next()
            )
            features["shared_ip_accounts"] = max(0, shared_ip_accounts - 1)
            
            # Check for VPN usage
            vpn_ips = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_IP")
                .has("is_vpn", 1)
                .count()
                .next()
            )
            features["is_vpn_user"] = vpn_ips > 0
            
            # Check for emulator usage
            emulator_devices = (
                self.client.V()
                .has("account", "account_id", account_id)
                .out("USES_DEVICE")
                .has("is_emulator", 1)
                .count()
                .next()
            )
            features["is_emulator_user"] = emulator_devices > 0
            
        except Exception as e:
            logger.error(f"Error getting features for {account_id}: {e}")
        
        return features
    
    def _extract_props_from_map(self, element_map: Dict) -> Dict[str, Any]:
        """Extract properties from an elementMap result."""
        props = {}
        for key, value in element_map.items():
            # Skip Gremlin special keys (T.id, T.label)
            if key == T.id:
                props["_id"] = str(value)
            elif key == T.label:
                props["_label"] = value
            else:
                # Handle list values (Gremlin sometimes wraps values)
                if isinstance(value, list) and len(value) > 0:
                    props[key] = value[0]
                else:
                    props[key] = value
        return props
    
    def _get_vertex_properties(self, vertex) -> Dict[str, Any]:
        """Extract properties from a vertex (legacy method - avoid using in loops)."""
        props = {"id": str(vertex.id)}
        try:
            value_map = self.client.V(vertex).value_map().next()
            for key, value in value_map.items():
                if isinstance(value, list) and len(value) > 0:
                    props[key] = value[0]
                else:
                    props[key] = value
        except Exception as e:
            logger.debug(f"Error getting vertex properties: {e}")
        return props
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if not self.client:
            return {}
        
        try:
            summary = self.client.call("aerospike.graph.admin.metadata.summary").next()
            return {
                "total_vertices": summary.get("Total vertex count", 0),
                "total_edges": summary.get("Total edge count", 0),
                "vertex_counts": summary.get("Vertex count by label", {}),
                "edge_counts": summary.get("Edge count by label", {})
            }
        except Exception as e:
            logger.error(f"Error getting graph summary: {e}")
            return {}
