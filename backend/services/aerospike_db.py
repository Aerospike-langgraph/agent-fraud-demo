"""
Aerospike DB Service - Key-value storage for alerts, cases, artifacts, and traces.

Provides methods for:
- Loading alerts from CSV or Aerospike
- Storing investigation cases and artifacts
- Persisting trace events for audit
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import csv
from pathlib import Path

logger = logging.getLogger("agentic_fraud.db")


class AerospikeDBService:
    """Service for interacting with Aerospike DB for metadata storage."""
    
    def __init__(
        self,
        host: str = None,
        port: int = 3000,
        namespace: str = "fraud_demo",
        data_dir: str = None
    ):
        self.host = host or os.environ.get("AEROSPIKE_HOST", "localhost")
        self.port = port
        self.namespace = namespace
        self.client = None
        
        # Path to CSV data for fallback/initial load
        self.data_dir = data_dir or os.environ.get(
            "DATA_DIR", 
            "/Users/jnemade/Documents/Aerospike/data/synthetic_fraud_data"
        )
        
        # In-memory caches (for demo simplicity)
        self._alerts_cache: Dict[str, Dict] = {}
        self._cases_cache: Dict[str, Dict] = {}
        self._artifacts_cache: Dict[str, Dict] = {}
        
        # Load alerts from CSV on init
        self._load_alerts_from_csv()
    
    def connect(self) -> bool:
        """Connect to Aerospike DB (optional - we can use CSV for demo)."""
        try:
            import aerospike
            config = {"hosts": [(self.host, self.port)]}
            self.client = aerospike.client(config).connect()
            logger.info(f"Connected to Aerospike DB at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Aerospike DB: {e}")
            logger.info("Using in-memory storage with CSV data")
            return False
    
    def close(self):
        """Close DB connection."""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from Aerospike DB")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
    
    def _load_alerts_from_csv(self):
        """Load alerts from synthetic data CSV."""
        alerts_path = Path(self.data_dir) / "alerts.csv"
        
        if not alerts_path.exists():
            logger.warning(f"Alerts CSV not found: {alerts_path}")
            return
        
        try:
            with open(alerts_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    alert_id = row.get("alert_id")
                    if alert_id:
                        self._alerts_cache[alert_id] = {
                            "alert_id": alert_id,
                            "account_id": row.get("account_id"),
                            "created_at": row.get("created_at"),
                            "risk_score": float(row.get("risk_score", 0)),
                            "risk_bucket": row.get("risk_bucket", "high"),
                            "reason": row.get("reason", ""),
                            "status": row.get("status", "open")
                        }
            
            logger.info(f"Loaded {len(self._alerts_cache)} alerts from CSV")
            
        except Exception as e:
            logger.error(f"Error loading alerts from CSV: {e}")
    
    def get_all_alerts(
        self,
        status: str = None,
        risk_bucket: str = None,
        min_risk_score: float = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Get all alerts with optional filtering."""
        alerts = list(self._alerts_cache.values())
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.get("status") == status]
        
        if risk_bucket:
            alerts = [a for a in alerts if a.get("risk_bucket") == risk_bucket]
        
        if min_risk_score is not None:
            alerts = [a for a in alerts if a.get("risk_score", 0) >= min_risk_score]
        
        # Sort by risk score descending
        alerts.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        
        # Apply limit
        if limit:
            alerts = alerts[:limit]
        
        return alerts
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert by ID."""
        return self._alerts_cache.get(alert_id)
    
    def get_alert_by_account_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get alert for a specific account."""
        for alert in self._alerts_cache.values():
            if alert.get("account_id") == account_id:
                return alert
        return None
    
    def create_case(self, case_id: str, alert_id: str, suspect_account_id: str) -> Dict[str, Any]:
        """Create a new investigation case."""
        case = {
            "case_id": case_id,
            "alert_id": alert_id,
            "suspect_account_id": suspect_account_id,
            "created_at": datetime.now().isoformat(),
            "status": "open",
            "workflow_status": "pending"
        }
        self._cases_cache[case_id] = case
        logger.info(f"Created case {case_id} for alert {alert_id}")
        return case
    
    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get a case by ID."""
        return self._cases_cache.get(case_id)
    
    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a case."""
        if case_id in self._cases_cache:
            self._cases_cache[case_id].update(updates)
            self._cases_cache[case_id]["updated_at"] = datetime.now().isoformat()
        return self._cases_cache.get(case_id)
    
    def save_artifact(
        self,
        case_id: str,
        artifact_type: str,
        artifact_data: Any,
        version: int = 1
    ) -> str:
        """Save an artifact (subgraph, evidence, report) for a case."""
        artifact_key = f"{case_id}:{artifact_type}:{version}"
        
        artifact = {
            "key": artifact_key,
            "case_id": case_id,
            "type": artifact_type,
            "version": version,
            "data": artifact_data,
            "created_at": datetime.now().isoformat()
        }
        
        self._artifacts_cache[artifact_key] = artifact
        logger.info(f"Saved artifact {artifact_key}")
        return artifact_key
    
    def get_artifact(
        self,
        case_id: str,
        artifact_type: str,
        version: int = None
    ) -> Optional[Dict[str, Any]]:
        """Get an artifact. If version is None, returns latest."""
        if version is not None:
            key = f"{case_id}:{artifact_type}:{version}"
            return self._artifacts_cache.get(key)
        
        # Find latest version
        matching = [
            (k, v) for k, v in self._artifacts_cache.items()
            if k.startswith(f"{case_id}:{artifact_type}:")
        ]
        
        if not matching:
            return None
        
        # Sort by version (last part of key)
        matching.sort(key=lambda x: int(x[0].split(":")[-1]), reverse=True)
        return matching[0][1]
    
    def append_trace_event(self, case_id: str, event: Dict[str, Any]):
        """Append a trace event for a case."""
        event["timestamp"] = datetime.now().isoformat()
        
        trace_key = f"trace:{case_id}"
        if trace_key not in self._artifacts_cache:
            self._artifacts_cache[trace_key] = {
                "case_id": case_id,
                "events": []
            }
        
        self._artifacts_cache[trace_key]["events"].append(event)
    
    def get_trace_events(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all trace events for a case."""
        trace_key = f"trace:{case_id}"
        trace = self._artifacts_cache.get(trace_key, {})
        return trace.get("events", [])
    
    def get_account_data(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account data from accounts CSV."""
        accounts_path = Path(self.data_dir) / "accounts.csv"
        
        if not accounts_path.exists():
            return None
        
        try:
            with open(accounts_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("account_id") == account_id:
                        return dict(row)
        except Exception as e:
            logger.error(f"Error reading account data: {e}")
        
        return None
    
    def get_case_manifest(self) -> Optional[Dict[str, Any]]:
        """Get the case manifest with ground truth."""
        manifest_path = Path(self.data_dir) / "case_manifest.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
        except Exception as e:
            logger.error(f"Error reading case manifest: {e}")
            return None
