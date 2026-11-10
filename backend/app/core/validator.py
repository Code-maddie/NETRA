"""
NETRA Network Configuration and Reachability Validator
Validates node counts, endpoint selections, graph connectivity, and path existence.
"""
from typing import Dict, Any, List, Optional
import networkx as nx

from app.config import settings

class NetworkValidator:
    @staticmethod
    def validate_configuration(
        node_count: Any,
        topology_type: str,
        density: str = "medium"
    ) -> Dict[str, Any]:
        """Validates configuration parameters prior to network generation."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate node count type and value
        if not isinstance(node_count, int) or isinstance(node_count, bool):
            errors.append(f"Node count must be an integer. Received: {type(node_count).__name__}")
        else:
            if node_count < settings.MIN_NODES:
                errors.append(f"Node count {node_count} is invalid. Minimum allowed is {settings.MIN_NODES} node.")
            elif node_count > settings.MAX_NODES:
                errors.append(f"Node count {node_count} exceeds maximum allowed boundary of {settings.MAX_NODES} nodes.")
            elif node_count == 1:
                warnings.append("Single-node network configured. Topology can be rendered, but routing experiments require at least 2 nodes.")

        # Validate topology
        if not topology_type or topology_type.lower() not in settings.SUPPORTED_TOPOLOGIES:
            errors.append(
                f"Invalid topology '{topology_type}'. Supported topologies: {settings.SUPPORTED_TOPOLOGIES}"
            )

        # Validate density
        if density and density.lower() not in settings.SUPPORTED_DENSITIES:
            warnings.append(f"Unknown density '{density}'. Defaulting to 'medium'.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config": {
                "node_count": node_count if isinstance(node_count, int) else None,
                "topology_type": topology_type,
                "density": density
            }
        }

    @staticmethod
    def validate_network_and_endpoints(
        topology_data: Dict[str, Any],
        source: Optional[int],
        destination: Optional[int]
    ) -> Dict[str, Any]:
        """
        Validates graph connectivity and whether a feasible route exists
        between the chosen source and destination nodes.
        """
        errors: List[str] = []
        warnings: List[str] = []
        details: Dict[str, Any] = {}

        nodes = topology_data.get("nodes", [])
        links = topology_data.get("links", [])
        node_ids = {n["id"] for n in nodes}
        num_nodes = len(nodes)

        # Special Case: Single node
        if num_nodes == 1:
            return {
                "valid": False,
                "is_single_node": True,
                "errors": ["Single-node network: Valid topology generated, but two-endpoint routing requires at least 2 nodes."],
                "warnings": warnings,
                "details": {"node_count": 1, "link_count": 0}
            }

        # Build NetworkX graph for topology verification
        G = nx.Graph()
        for n in nodes:
            G.add_node(n["id"])
        for link in links:
            if link.get("status", "active") == "active":
                G.add_edge(link["source"], link["target"])

        # Check endpoints presence
        if source is None:
            errors.append("Source node must be specified.")
        elif source not in node_ids:
            errors.append(f"Source node {source} does not exist in the generated network.")

        if destination is None:
            errors.append("Destination node must be specified.")
        elif destination not in node_ids:
            errors.append(f"Destination node {destination} does not exist in the generated network.")

        if source is not None and destination is not None:
            if source == destination:
                errors.append(f"Source and destination must be distinct endpoints. Both set to {source}.")
            elif source in node_ids and destination in node_ids:
                # Reachability verification
                if nx.has_path(G, source, destination):
                    shortest_hop = nx.shortest_path_length(G, source, destination)
                    details["path_exists"] = True
                    details["min_hops"] = shortest_hop
                else:
                    errors.append(
                        f"Destination node {destination} is unreachable from source node {source}. "
                        f"The network contains {nx.number_connected_components(G)} disconnected components."
                    )
                    details["path_exists"] = False

        details["is_connected"] = nx.is_connected(G)
        details["connected_components"] = nx.number_connected_components(G)
        details["node_count"] = num_nodes
        details["active_link_count"] = G.number_of_edges()

        return {
            "valid": len(errors) == 0,
            "is_single_node": False,
            "errors": errors,
            "warnings": warnings,
            "details": details
        }
