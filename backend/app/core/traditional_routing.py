"""
NETRA Traditional Routing Algorithms
Implements Dijkstra's Shortest Path (static weight & dynamic delay-sensitive)
and Least-Loaded Routing with execution timing.
"""
import time
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx

class TraditionalRouter:
    @staticmethod
    def _build_nx_graph(
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        metric: str = "delay"
    ) -> nx.Graph:
        """Constructs a NetworkX graph containing active links with appropriate edge weights."""
        G = nx.Graph()
        for node in nodes:
            G.add_node(node["id"])

        for link in links:
            if link.get("status", "active") != "active":
                continue  # Skip failed links

            u = link["source"]
            v = link["target"]
            base_delay = link.get("base_delay_ms", 5.0)
            utilization = link.get("utilization", 0.0)

            if metric == "hop":
                weight = 1.0
            elif metric == "capacity":
                utilization = float(utilization)
                normalized_capacity = float(link.get("capacity_mbps", 100.0))
                weight = base_delay * (1.0 + utilization) / max(1.0, normalized_capacity / 100.0)
            elif metric == "least_loaded":
                # Heavily penalize high utilization
                weight = base_delay * (1.0 + 5.0 * (utilization ** 2))
            else:  # "delay" / dynamic latency
                # Queuing delay factor: effective_delay = base_delay / (1 - min(0.95, utilization))
                effective_delay = base_delay / (1.0 - min(0.92, utilization))
                weight = effective_delay

            G.add_edge(u, v, weight=weight, link_id=link["id"], base_delay=base_delay, utilization=utilization)

        return G

    @classmethod
    def compute_route(
        cls,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        source: int,
        destination: int,
        algorithm: str = "dijkstra_dynamic",
        previous_path: Optional[List[int]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Computes a route between source and destination using the specified traditional algorithm.
        
        Returns:
          Dictionary with path, total_cost, estimated_delay_ms, computation_time_ms, and success flag.
        """
        start_time = time.perf_counter()

        metric_map = {
            "dijkstra_static": "hop",
            "dijkstra_dynamic": "delay",
            "least_loaded": "least_loaded",
            "capacity_aware": "capacity",
            "ecmp": "hop",
            "cadj": "delay"
        }
        metric = metric_map.get(algorithm, "delay")
        G = cls._build_nx_graph(nodes, links, metric=metric)

        if not G.has_node(source) or not G.has_node(destination):
            computation_time = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": False,
                "path": [],
                "hops": 0,
                "total_cost": float("inf"),
                "estimated_delay_ms": float("inf"),
                "computation_time_ms": round(computation_time, 4),
                "algorithm": algorithm,
                "error": "Endpoints not present in active network"
            }

        try:
            if algorithm == "ecmp":
                candidates = [
                    list(path) for path in nx.all_shortest_paths(G, source, destination, weight="weight")
                ]
                if not candidates:
                    raise nx.NetworkXNoPath
                previous_path = previous_path or kwargs.get("previous_path")
                if previous_path in candidates:
                    selected = candidates[(candidates.index(previous_path) + 1) % len(candidates)]
                else:
                    selected = candidates[0]
                total_weight = nx.shortest_path_length(G, source=source, target=destination, weight="weight")
                computation_time = (time.perf_counter() - start_time) * 1000.0
                return {
                    "success": True,
                    "path": [int(node) for node in selected],
                    "equal_cost_paths": len(candidates),
                    "hops": len(selected) - 1,
                    "total_cost": round(total_weight, 3),
                    "estimated_delay_ms": round(sum(G[u][v].get("weight", 5.0) for u, v in zip(selected[:-1], selected[1:])), 2),
                    "computation_time_ms": round(computation_time, 4),
                    "algorithm": algorithm,
                    "error": None
                }

            if algorithm == "cadj":
                # Hysteresis-tuned routing: evaluate candidate paths and apply stickiness penalty to prevent herding/oscillation
                candidates = cls.get_candidate_paths(nodes, links, source, destination, k=4)
                if not candidates:
                    raise nx.NetworkXNoPath

                def score_path(cand_path: List[int]) -> float:
                    # Delay sum along path
                    d = 0.0
                    for i in range(len(cand_path) - 1):
                        if G.has_edge(cand_path[i], cand_path[i + 1]):
                            d += G[cand_path[i]][cand_path[i + 1]].get("weight", 5.0)
                        else:
                            return float("inf")
                    # Hysteresis penalty if switching from previous path
                    prev = previous_path or kwargs.get("previous_path")
                    if prev and cand_path != prev:
                        d += 0.05 * d + 0.5  # stickiness penalty
                    return d

                best_path = min(candidates, key=score_path)
                total_delay = 0.0
                for i in range(len(best_path) - 1):
                    total_delay += G[best_path[i]][best_path[i + 1]].get("weight", 5.0)

                computation_time = (time.perf_counter() - start_time) * 1000.0
                return {
                    "success": True,
                    "path": [int(n) for n in best_path],
                    "hops": len(best_path) - 1,
                    "total_cost": round(total_delay, 3),
                    "estimated_delay_ms": round(total_delay, 2),
                    "computation_time_ms": round(computation_time, 4),
                    "algorithm": "cadj",
                    "error": None
                }

            path = nx.shortest_path(G, source=source, target=destination, weight="weight")
            total_weight = nx.shortest_path_length(G, source=source, target=destination, weight="weight")
            
            # Calculate total estimated physical delay along path
            total_delay = 0.0
            for i in range(len(path) - 1):
                edge_data = G.get_edge_data(path[i], path[i + 1])
                total_delay += edge_data.get("weight", 5.0)

            computation_time = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": True,
                "path": [int(node_id) for node_id in path],
                "hops": len(path) - 1,
                "total_cost": round(total_weight, 3),
                "estimated_delay_ms": round(total_delay, 2),
                "computation_time_ms": round(computation_time, 4),
                "algorithm": algorithm,
                "error": None
            }
        except nx.NetworkXNoPath:
            computation_time = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": False,
                "path": [],
                "hops": 0,
                "total_cost": float("inf"),
                "estimated_delay_ms": float("inf"),
                "computation_time_ms": round(computation_time, 4),
                "algorithm": algorithm,
                "error": f"No active path exists between node {source} and node {destination}"
            }

    @classmethod
    def get_candidate_paths(
        cls,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        source: int,
        destination: int,
        k: int = 4
    ) -> List[List[int]]:
        """Precomputes up to k simple loop-free paths, candidate 0 being static Dijkstra."""
        from itertools import islice
        G = cls._build_nx_graph(nodes, links, metric="hop")
        if not G.has_node(source) or not G.has_node(destination):
            return []

        try:
            paths = list(islice(nx.shortest_simple_paths(G, source, destination, weight="weight"), k))
            return [[int(node) for node in p] for p in paths]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
