"""Destination-aware routing environment used to train and evaluate the PPO agent.

The environment exposes only active, useful next-hop candidates. Candidate link
features include an estimate of the remaining hop distance to the destination,
so the policy can distinguish a promising neighbor from an arbitrary one.
"""
from collections import deque
import heapq
from typing import Dict, Any, List, Tuple, Optional
import math
import numpy as np


class NetworkRoutingEnv:
    """A simple-hop routing environment with loop prevention and reward shaping."""

    def __init__(
        self,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        source: int,
        destination: int,
        max_hops: int = 50,
        max_degree: int = 10,
    ):
        self.nodes = nodes
        self.links = links
        self.source = source
        self.destination = destination
        self.max_hops = max_hops
        self.max_degree = max_degree
        self.node_count = len(nodes)

        self.adj: Dict[int, List[Dict[str, Any]]] = {n["id"]: [] for n in nodes}
        for link in links:
            u, v = link["source"], link["target"]
            if u in self.adj and v in self.adj:
                self.adj[u].append({"neighbor": v, "link": link})
                self.adj[v].append({"neighbor": u, "link": link})

        # Keep the checkpoint tensor dimensions stable (3 + 10 * 4 = 43), but
        # use the last feature per neighbor for destination distance rather than
        # a redundant destination-is-neighbor flag.
        self.state_dim = 3 + self.max_degree * 4
        self.action_dim = self.max_degree
        self.current_node = source
        self.hop_count = 0
        self.visited_nodes: List[int] = [source]
        self.accumulated_delay_ms = 0.0
        self.accumulated_cost = 0.0
        self.done = False
        self._distance_cache: Optional[Dict[int, int]] = None
        self._cost_cache: Optional[Dict[int, float]] = None

    def _invalidate_caches(self) -> None:
        """Clear graph-derived features after the visited-node set changes."""
        self._distance_cache = None
        self._cost_cache = None

    def reset(self, source: Optional[int] = None, destination: Optional[int] = None) -> np.ndarray:
        if source is not None:
            self.source = source
        if destination is not None:
            self.destination = destination
        self.current_node = self.source
        self.hop_count = 0
        self.visited_nodes = [self.source]
        self.accumulated_delay_ms = 0.0
        self.accumulated_cost = 0.0
        self.done = self.source == self.destination
        self._invalidate_caches()
        return self._get_observation()

    def _distance_map(self) -> Dict[int, int]:
        """Shortest active-link hop distance to destination, avoiding visited nodes.

        The current/previously visited nodes are blocked while searching from each
        candidate, preventing the policy from selecting a neighbor whose only way
        to the destination is to loop back through the route it has already taken.
        """
        if self._distance_cache is not None:
            return self._distance_cache
        if self.destination not in self.adj:
            self._distance_cache = {}
            return self._distance_cache

        blocked = set(self.visited_nodes)
        blocked.discard(self.destination)
        distances: Dict[int, int] = {self.destination: 0}
        queue = deque([self.destination])

        while queue:
            node = queue.popleft()
            for item in self.adj.get(node, []):
                link = item["link"]
                neighbor = item["neighbor"]
                if link.get("status", "active") != "active":
                    continue
                if neighbor in blocked or neighbor in distances:
                    continue
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
        self._distance_cache = distances
        return distances

    @staticmethod
    def _link_cost(link: Dict[str, Any]) -> float:
        base_delay = max(0.1, float(link.get("base_delay_ms", 5.0)))
        utilization = min(0.99, max(0.0, float(link.get("utilization", 0.0))))
        return base_delay / max(0.08, 1.0 - utilization)

    def _cost_map(self) -> Dict[int, float]:
        """Dijkstra cost-to-go estimate using current delay/utilization values."""
        if self._cost_cache is not None:
            return self._cost_cache
        if self.destination not in self.adj:
            self._cost_cache = {}
            return self._cost_cache
        blocked = set(self.visited_nodes)
        blocked.discard(self.destination)
        distances: Dict[int, float] = {self.destination: 0.0}
        queue: List[Tuple[float, int]] = [(0.0, self.destination)]
        while queue:
            cost, node = heapq.heappop(queue)
            if cost > distances.get(node, math.inf):
                continue
            for item in self.adj.get(node, []):
                link = item["link"]
                neighbor = item["neighbor"]
                if link.get("status", "active") != "active" or neighbor in blocked:
                    continue
                new_cost = cost + self._link_cost(link)
                if new_cost < distances.get(neighbor, math.inf):
                    distances[neighbor] = new_cost
                    heapq.heappush(queue, (new_cost, neighbor))
        self._cost_cache = distances
        return distances

    def _get_neighbors(self, node: int) -> List[Dict[str, Any]]:
        """Return active, loop-free next hops that can still reach the destination."""
        hop_distances = self._distance_map()
        cost_distances = self._cost_map()
        candidates = []
        for item in self.adj.get(node, []):
            link = item["link"]
            neighbor = item["neighbor"]
            if link.get("status", "active") != "active":
                continue
            if neighbor in self.visited_nodes:
                continue
            if neighbor != self.destination and neighbor not in hop_distances:
                continue
            candidates.append(item)

        def key(item: Dict[str, Any]) -> Tuple[float, float, int]:
            neighbor = item["neighbor"]
            estimated_total = self._link_cost(item["link"]) + cost_distances.get(
                neighbor, 0.0 if neighbor == self.destination else math.inf
            )
            return (estimated_total, float(item["link"].get("utilization", 0.0)), int(neighbor))

        return sorted(candidates, key=key)[: self.max_degree]

    def get_action_mask(self) -> np.ndarray:
        """Mask only invalid moves; every viable loop-free candidate remains learnable."""
        mask = np.zeros(self.action_dim, dtype=bool)
        neighbors = self._get_neighbors(self.current_node)
        # _get_neighbors excludes visited nodes and candidates that cannot reach
        # the destination without revisiting the existing path. Do not mask a
        # valid but expensive route using Dijkstra's own score: that would bias
        # the RL policy toward the baseline it is supposed to be compared with.
        mask[:len(neighbors)] = True
        return mask

    def _get_observation(self) -> np.ndarray:
        obs = np.zeros(self.state_dim, dtype=np.float32)
        obs[0] = float(self.current_node) / max(1.0, float(self.node_count - 1))
        obs[1] = float(self.destination) / max(1.0, float(self.node_count - 1))
        obs[2] = min(1.0, float(self.hop_count) / max(1.0, float(self.max_hops)))

        cost_distances = self._cost_map()
        neighbors = self._get_neighbors(self.current_node)
        cost_scale = 250.0

        for i in range(self.max_degree):
            offset = 3 + i * 4
            if i >= len(neighbors):
                continue
            item = neighbors[i]
            link = item["link"]
            neighbor = item["neighbor"]
            base_delay = float(link.get("base_delay_ms", 5.0))
            utilization = float(link.get("utilization", 0.0))
            remaining_cost = 0.0 if neighbor == self.destination else cost_distances.get(neighbor, cost_scale)
            # Candidate identity replaces a redundant always-one active flag.
            # This helps the policy distinguish equal-cost neighbors while
            # retaining the established 43-element checkpoint input shape.
            obs[offset] = float(neighbor) / max(1.0, float(self.node_count - 1))
            obs[offset + 1] = min(1.0, max(0.0, base_delay / 50.0))
            obs[offset + 2] = min(1.0, max(0.0, utilization))
            obs[offset + 3] = min(1.0, max(0.0, float(remaining_cost) / cost_scale))
        return obs

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if self.done:
            return self._get_observation(), 0.0, True, {"path": self.visited_nodes}

        neighbors = self._get_neighbors(self.current_node)
        mask = self.get_action_mask()
        if not mask.any() or action < 0 or action >= len(neighbors) or not mask[action]:
            self.done = True
            return self._get_observation(), -5.0, True, {
                "success": False,
                "reason": "No valid unvisited next hop can reach the destination",
                "path": self.visited_nodes,
            }

        before_costs = self._cost_map()
        distance_before = min(
            (self._link_cost(item["link"]) + before_costs.get(item["neighbor"], math.inf) for item in neighbors),
            default=math.inf,
        )

        chosen = neighbors[action]
        chosen_nbr = chosen["neighbor"]
        chosen_link = chosen["link"]
        base_delay = float(chosen_link.get("base_delay_ms", 5.0))
        utilization = min(0.99, max(0.0, float(chosen_link.get("utilization", 0.0))))
        effective_delay = base_delay / max(0.08, 1.0 - utilization)

        self.accumulated_delay_ms += effective_delay
        self.accumulated_cost += effective_delay
        self.visited_nodes.append(chosen_nbr)
        self._invalidate_caches()
        self.current_node = chosen_nbr
        self.hop_count += 1

        reward = -0.15 - 0.02 * min(50.0, effective_delay)
        if utilization > 0.8:
            reward -= 1.5 * (utilization ** 2)

        if self.current_node == self.destination:
            reward += 10.0 + max(0.0, (15.0 - self.hop_count) * 0.5)
            self.done = True
            return self._get_observation(), reward, True, {
                "success": True,
                "path": self.visited_nodes.copy(),
                "hops": self.hop_count,
                "total_delay_ms": round(self.accumulated_delay_ms, 2),
            }

        # Potential-based shaping: reward progress toward the destination, but
        # retain the latency/congestion terms so a longer low-delay route can win.
        after_neighbors = self._get_neighbors(self.current_node)
        after_costs = self._cost_map()
        distance_after = min(
            (self._link_cost(item["link"]) + after_costs.get(item["neighbor"], math.inf) for item in after_neighbors),
            default=math.inf,
        )
        if math.isfinite(distance_before) and math.isfinite(distance_after):
            # Small potential-based shaping. The immediate delay penalty remains
            # active, so the potential does not overwhelm the real objective.
            reward += 0.01 * (distance_before - distance_after)
        else:
            reward -= 3.0
            self.done = True
            return self._get_observation(), reward, True, {
                "success": False,
                "reason": "No unvisited route to destination remains",
                "path": self.visited_nodes.copy(),
            }

        if self.hop_count >= self.max_hops:
            reward -= 5.0
            self.done = True
            return self._get_observation(), reward, True, {
                "success": False,
                "reason": "Maximum hop limit reached",
                "path": self.visited_nodes.copy(),
            }

        return self._get_observation(), reward, False, {"success": False, "path": self.visited_nodes.copy()}
