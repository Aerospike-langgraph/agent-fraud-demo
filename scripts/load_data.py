#!/usr/bin/env python3
"""
Load synthetic fraud data into Aerospike Graph using BULK LOADER API.

This is much faster than individual Gremlin queries.

Usage:
    python scripts/load_data.py [--data-dir PATH] [--graph-host HOST]
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.driver.aiohttp.transport import AiohttpTransport
from gremlin_python.process.anonymous_traversal import traversal


def convert_to_bulk_format(data_dir: Path, output_dir: Path):
    """
    Convert synthetic fraud data CSVs to Aerospike Graph bulk loader format.
    
    Bulk loader expects:
    - vertices/<label>.csv with columns: ~id, ~label, property1, property2, ...
    - edges/<label>.csv with columns: ~id, ~from, ~to, ~label, property1, property2, ...
    """
    vertices_dir = output_dir / "vertices"
    edges_dir = output_dir / "edges"
    vertices_dir.mkdir(parents=True, exist_ok=True)
    edges_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert accounts to vertices format
    print("Converting accounts...")
    accounts_path = data_dir / "accounts.csv"
    if accounts_path.exists():
        with open(accounts_path) as f_in, open(vertices_dir / "account.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~label", "account_id:String", "user_id:String", "country:String", 
                           "channel:String", "kyc_level:String", "status:String", "is_fraud:Int", "risk_score:Double"])
            count = 0
            for row in reader:
                writer.writerow([
                    row["account_id"],  # ~id
                    "account",  # ~label
                    row["account_id"],
                    row.get("user_id", ""),
                    row.get("country", ""),
                    row.get("channel", ""),
                    row.get("kyc_level", ""),
                    row.get("status", "active"),
                    int(row.get("is_fraud", 0)),
                    float(row.get("risk_score", 0))
                ])
                count += 1
        print(f"  Converted {count} accounts")
    
    # Convert devices to vertices format
    print("Converting devices...")
    devices_path = data_dir / "devices.csv"
    if devices_path.exists():
        with open(devices_path) as f_in, open(vertices_dir / "device.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~label", "device_id:String", "device_type:String", 
                           "is_emulator:Int", "is_automation:Int"])
            count = 0
            for row in reader:
                writer.writerow([
                    row["device_id"],  # ~id
                    "device",  # ~label
                    row["device_id"],
                    row.get("device_type", ""),
                    int(row.get("is_emulator", 0)),
                    int(row.get("is_automation", 0))
                ])
                count += 1
        print(f"  Converted {count} devices")
    
    # Convert IPs to vertices format
    print("Converting IPs...")
    ips_path = data_dir / "ips.csv"
    if ips_path.exists():
        with open(ips_path) as f_in, open(vertices_dir / "ip.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~label", "ip_id:String", "ip:String", 
                           "is_vpn:Int", "reputation_score:Double"])
            count = 0
            for row in reader:
                writer.writerow([
                    row["ip_id"],  # ~id
                    "ip",  # ~label
                    row["ip_id"],
                    row.get("ip", ""),
                    int(row.get("is_vpn", 0)),
                    float(row.get("reputation_score", 0))
                ])
                count += 1
        print(f"  Converted {count} IPs")
    
    # Convert account-device edges
    print("Converting account-device edges...")
    acct_device_path = data_dir / "account_device.csv"
    if acct_device_path.exists():
        with open(acct_device_path) as f_in, open(edges_dir / "USES_DEVICE.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~from", "~to", "~label", "count:Int", "first_seen:String", "last_seen:String"])
            count = 0
            for row in reader:
                edge_id = f"{row['account_id']}_USES_DEVICE_{row['device_id']}"
                writer.writerow([
                    edge_id,
                    row["account_id"],
                    row["device_id"],
                    "USES_DEVICE",
                    int(row.get("count", 1)),
                    row.get("first_seen", ""),
                    row.get("last_seen", "")
                ])
                count += 1
        print(f"  Converted {count} account-device edges")
    
    # Convert account-IP edges
    print("Converting account-IP edges...")
    acct_ip_path = data_dir / "account_ip.csv"
    if acct_ip_path.exists():
        with open(acct_ip_path) as f_in, open(edges_dir / "USES_IP.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~from", "~to", "~label", "count:Int", "first_seen:String", "last_seen:String"])
            count = 0
            for row in reader:
                edge_id = f"{row['account_id']}_USES_IP_{row['ip_id']}"
                writer.writerow([
                    edge_id,
                    row["account_id"],
                    row["ip_id"],
                    "USES_IP",
                    int(row.get("count", 1)),
                    row.get("first_seen", ""),
                    row.get("last_seen", "")
                ])
                count += 1
        print(f"  Converted {count} account-IP edges")
    
    # Convert transactions (account-account edges)
    print("Converting transaction edges...")
    tx_path = data_dir / "transactions.csv"
    if tx_path.exists():
        with open(tx_path) as f_in, open(edges_dir / "TRANSACTS.csv", "w", newline="") as f_out:
            reader = csv.DictReader(f_in)
            writer = csv.writer(f_out)
            writer.writerow(["~id", "~from", "~to", "~label", "amount:Double", "timestamp:String"])
            count = 0
            for row in reader:
                from_acct = row.get("from_account_id") or row.get("from_account")
                to_acct = row.get("to_account_id") or row.get("to_account")
                if from_acct and to_acct:
                    tx_id = row.get("tx_id") or f"TX_{count}"
                    writer.writerow([
                        tx_id,
                        from_acct,
                        to_acct,
                        "TRANSACTS",
                        float(row.get("amount", 0)),
                        row.get("timestamp", "")
                    ])
                    count += 1
        print(f"  Converted {count} transaction edges")
    
    print(f"\nConversion complete! Output in: {output_dir}")
    return vertices_dir, edges_dir


def bulk_load_data(g, vertices_path: str, edges_path: str):
    """Use Aerospike Graph bulk loader API for fast data ingestion."""
    print(f"\nStarting bulk load...")
    print(f"  Vertices path: {vertices_path}")
    print(f"  Edges path: {edges_path}")
    
    try:
        result = (g
            .with_("evaluationTimeout", 2000000)
            .call("aerospike.graphloader.admin.bulk-load.load")
            .with_("aerospike.graphloader.vertices", vertices_path)
            .with_("aerospike.graphloader.edges", edges_path)
            .next())
        
        print("Bulk load started successfully!")
        return True, result
    except Exception as e:
        print(f"Bulk load failed: {e}")
        return False, str(e)


def wait_for_bulk_load(g, max_wait: int = 300):
    """Wait for bulk load to complete and show progress."""
    print("\nWaiting for bulk load to complete...")
    wait_time = 0
    check_interval = 5
    
    while wait_time < max_wait:
        time.sleep(check_interval)
        wait_time += check_interval
        
        try:
            status = g.call("aerospike.graphloader.admin.bulk-load.status").next()
            step = status.get("step", "unknown")
            complete = status.get("complete", False)
            
            if complete:
                print(f"✓ Bulk load completed! (took {wait_time}s)")
                return True
            else:
                print(f"  Status: {step} ({wait_time}s elapsed)...")
        except Exception as e:
            print(f"  Checking... ({wait_time}s)")
    
    print(f"Timeout after {max_wait}s")
    return False


def get_graph_summary(g):
    """Get graph statistics using Aerospike Graph admin API."""
    try:
        summary = g.call("aerospike.graph.admin.metadata.summary").next()
        return {
            "total_vertices": summary.get("Total vertex count", 0),
            "total_edges": summary.get("Total edge count", 0),
            "vertex_counts": summary.get("Vertex count by label", {}),
            "edge_counts": summary.get("Edge count by label", {})
        }
    except:
        # Fallback to Gremlin queries
        return {
            "total_vertices": g.V().count().next(),
            "total_edges": g.E().count().next()
        }


def main():
    parser = argparse.ArgumentParser(description="Load fraud data into Aerospike Graph (fast bulk loader)")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("DATA_DIR", "../data/synthetic_fraud_data"),
        help="Path to synthetic fraud data directory"
    )
    parser.add_argument(
        "--graph-host",
        default=os.environ.get("GRAPH_HOST_ADDRESS", "localhost"),
        help="Aerospike Graph host"
    )
    parser.add_argument(
        "--graph-port",
        type=int,
        default=8182,
        help="Aerospike Graph port"
    )
    parser.add_argument(
        "--output-dir",
        default=None,  # Will be set based on script location
        help="Output directory for converted CSV files (must be accessible by graph service)"
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip CSV conversion (use existing converted files)"
    )
    parser.add_argument(
        "--container-path",
        default=None,
        help="Path to converted files inside the graph container (default: /data/graph_csv)"
    )
    
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    
    # Default output dir is ./data/graph_csv relative to script's parent (project root)
    # Script is in scripts/, output to data/graph_csv (sibling to scripts)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "data" / "graph_csv"
    
    # Container path (where graph service will read from)
    if args.container_path:
        container_path = args.container_path
    else:
        container_path = "/data/graph_csv"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)
    
    # Step 1: Convert CSV files to bulk loader format
    if not args.skip_convert:
        print("=" * 60)
        print("Step 1: Converting CSV files to bulk loader format")
        print("=" * 60)
        print(f"Output directory (host): {output_dir}")
        print(f"Output directory (container): {container_path}")
        vertices_dir, edges_dir = convert_to_bulk_format(data_dir, output_dir)
    else:
        vertices_dir = output_dir / "vertices"
        edges_dir = output_dir / "edges"
        print("Skipping conversion, using existing files...")
    
    # Paths for bulk loader (inside container)
    container_vertices = f"{container_path}/vertices"
    container_edges = f"{container_path}/edges"
    
    # Step 2: Connect to graph
    print("\n" + "=" * 60)
    print("Step 2: Connecting to Aerospike Graph")
    print("=" * 60)
    print(f"Connecting to {args.graph_host}:{args.graph_port}...")
    
    try:
        url = f"ws://{args.graph_host}:{args.graph_port}/gremlin"
        connection = DriverRemoteConnection(
            url, "g",
            transport_factory=lambda: AiohttpTransport(call_from_event_loop=True)
        )
        g = traversal().with_remote(connection)
        
        # Test connection
        test = g.inject(0).next()
        print("✓ Connected successfully!")
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)
    
    # Step 3: Bulk load data
    print("\n" + "=" * 60)
    print("Step 3: Bulk loading data")
    print("=" * 60)
    
    success, result = bulk_load_data(g, container_vertices, container_edges)
    
    if success:
        # Wait for completion
        completed = wait_for_bulk_load(g)
        
        if completed:
            # Step 4: Get summary
            print("\n" + "=" * 60)
            print("Step 4: Graph Summary")
            print("=" * 60)
            
            summary = get_graph_summary(g)
            print(f"Total vertices: {summary.get('total_vertices', 'N/A')}")
            print(f"Total edges: {summary.get('total_edges', 'N/A')}")
            
            vertex_counts = summary.get('vertex_counts', {})
            if vertex_counts:
                print("\nVertex counts by label:")
                for label, count in vertex_counts.items():
                    print(f"  {label}: {count}")
            
            edge_counts = summary.get('edge_counts', {})
            if edge_counts:
                print("\nEdge counts by label:")
                for label, count in edge_counts.items():
                    print(f"  {label}: {count}")
    
    connection.close()
    print("\n" + "=" * 60)
    print("✓ Data loading complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
