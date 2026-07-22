"""
Kubernetes NetworkPolicy connection tracker module.

Tracks established connections and provides stateful evaluation
for traffic flows, maintaining connection state across evaluations.
"""

from typing import Optional
from traffic_matcher import TrafficFlow


class Connection:
    """Represents an established network connection."""

    def __init__(self, src_ip: str, dst_ip: str, dst_port: int,
                 protocol: str, state: str = "ESTABLISHED"):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.protocol = protocol
        self.state = state
        self.packet_count = 0
        self.byte_count = 0

    def matches_flow(self, flow: TrafficFlow) -> bool:
        """Check if this connection matches a traffic flow."""
        return (self.src_ip == flow.src_ip and
                self.dst_ip == flow.dst_ip and
                self.dst_port == flow.dst_port and
                self.protocol.upper() == flow.protocol.upper())

    def matches_return_flow(self, flow: TrafficFlow) -> bool:
        """Check if this connection matches a return traffic flow."""
        return (self.src_ip == flow.dst_ip and
                self.dst_ip == flow.src_ip and
                self.protocol.upper() == flow.protocol.upper())

    def to_dict(self) -> dict:
        """Convert connection to dictionary."""
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "state": self.state,
            "packet_count": self.packet_count,
            "byte_count": self.byte_count
        }

    def __repr__(self):
        return f"Connection({self.src_ip} -> {self.dst_ip}:{self.dst_port}/{self.protocol} [{self.state}])"


class ConnectionTracker:
    """Tracks network connections and their states."""

    def __init__(self):
        self.connections = []
        self.evaluation_log = []

    def add_connection(self, flow: TrafficFlow) -> Connection:
        """Add a new established connection from an allowed flow."""
        conn = Connection(
            src_ip=flow.src_ip,
            dst_ip=flow.dst_ip,
            dst_port=flow.dst_port,
            protocol=flow.protocol
        )
        self.connections.append(conn)
        return conn

    def find_established_connection(self, flow: TrafficFlow) -> Optional[Connection]:
        """Find an existing connection that matches this flow."""
        for conn in self.connections:
            if conn.state == "ESTABLISHED" and conn.matches_flow(flow):
                return conn
        return None

    def find_return_connection(self, flow: TrafficFlow) -> Optional[Connection]:
        """Find an established connection for return traffic."""
        for conn in self.connections:
            if conn.state == "ESTABLISHED" and conn.matches_return_flow(flow):
                return conn
        return None

    def is_established_traffic(self, flow: TrafficFlow) -> bool:
        """Check if traffic belongs to an established connection."""
        return self.find_established_connection(flow) is not None

    def is_return_traffic(self, flow: TrafficFlow) -> bool:
        """Check if traffic is return traffic for an established connection."""
        return self.find_return_connection(flow) is not None

    def record_evaluation(self, flow: TrafficFlow, verdict: str, reason: str):
        """Record an evaluation result in the log."""
        self.evaluation_log.append({
            "flow": str(flow),
            "verdict": verdict,
            "reason": reason
        })

    def get_connection_count(self) -> int:
        """Get the total number of tracked connections."""
        return len(self.connections)

    def get_established_count(self) -> int:
        """Get the number of established connections."""
        return sum(1 for c in self.connections if c.state == "ESTABLISHED")

    def close_connection(self, flow: TrafficFlow):
        """Close a connection matching the given flow."""
        conn = self.find_established_connection(flow)
        if conn:
            conn.state = "CLOSED"

    def get_stats(self) -> dict:
        """Get connection tracker statistics."""
        return {
            "total_connections": self.get_connection_count(),
            "established": self.get_established_count(),
            "evaluations": len(self.evaluation_log)
        }

    def reset(self):
        """Reset all tracked connections and logs."""
        self.connections = []
        self.evaluation_log = []
