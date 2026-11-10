"""
NETRA Dynamic Discrete-Event Network Simulator
Executes discrete-step network simulation, updates link utilization and queues,
injects dynamic link failures/recoveries, computes live telemetry, and records true events.
"""
import copy
import random
import time
from typing import Dict, Any, List, Optional

from app.config import settings
from app.core.traffic import generate_traffic_schedule
from app.core.traditional_routing import TraditionalRouter
from app.core.rl.environment import NetworkRoutingEnv
from app.core.rl.ppo_agent import PPOAgent
from app.core.rl.candidate_agent import CandidatePPOAgent
from app.core.metrics import compute_simulation_metrics

class NetworkSimulator:
    def __init__(
        self,
        topology_data: Dict[str, Any],
        source: int,
        destination: int,
        routing_method: str = "dijkstra_dynamic",
        traffic_pattern: str = "mixed",
        dynamic_conditions: bool = True,
        total_steps: int = 30,
        seed: int = 42,
        ppo_agent: Optional[PPOAgent] = None,
        candidate_agent: Optional[CandidatePPOAgent] = None
    ):
        self.simulation_id = f"sim_{int(time.time() * 1000)}"
        self.topology_data = copy.deepcopy(topology_data)
        self.nodes = self.topology_data["nodes"]
        self.links = self.topology_data["links"]
        self.source = source
        self.destination = destination
        self.routing_method = routing_method
        self.traffic_pattern = traffic_pattern
        self.dynamic_conditions = dynamic_conditions
        self.total_steps = total_steps
        self.seed = seed
        self.rng = random.Random(seed)

        # Lookup maps
        self.links_by_id = {l["id"]: l for l in self.links}
        self.link_endpoint_map = {
            (min(l["source"], l["target"]), max(l["source"], l["target"])): l["id"]
            for l in self.links
        }

        # Initialize traffic schedule
        self.traffic_schedule = generate_traffic_schedule(
            pattern=traffic_pattern,
            total_steps=total_steps,
            # 2,500 x 1,500-byte packets per 500 ms is 60 Mbps offered load.
            # This is high enough to expose bottlenecks on 100 Mbps links while
            # remaining below the capacity of the faster links in the model.
            base_rate_packets=2500,
            seed=seed
        )

        # RL agent instances
        self.ppo_agent = ppo_agent or PPOAgent()
        self.candidate_agent = candidate_agent or CandidatePPOAgent()
        self.shield_fallback_count = 0
        self.total_shield_evals = 0

        # Inject a failure on the current delay-sensitive baseline path when
        # possible. Failing an arbitrary irrelevant edge makes the benchmark
        # look dynamic without actually challenging either routing strategy.
        self.failure_schedule: Dict[int, Dict[str, Any]] = {}
        if dynamic_conditions and len(self.links) > 2:
            baseline = TraditionalRouter.compute_route(
                self.nodes, self.links, self.source, self.destination,
                algorithm="dijkstra_dynamic",
            )
            path_candidates = []
            if baseline.get("success"):
                path = baseline.get("path", [])
                path_candidates = [
                    self._get_link_id(path[i], path[i + 1])
                    for i in range(len(path) - 1)
                ]
                path_candidates = [link_id for link_id in path_candidates if link_id]
            candidate_links = path_candidates or [l["id"] for l in self.links]
            failed_link_id = self.rng.choice(candidate_links)
            fail_step = max(3, total_steps // 4)
            recover_step = min(total_steps - 2, fail_step + (total_steps // 3))
            self.failure_schedule[fail_step] = {"action": "fail", "link_id": failed_link_id}
            self.failure_schedule[recover_step] = {"action": "recover", "link_id": failed_link_id}

        # Simulation state
        self.current_step = 0
        self.is_completed = False
        self.events: List[Dict[str, Any]] = []
        self.packet_history: List[Dict[str, Any]] = []
        self.step_metrics_timeline: List[Dict[str, Any]] = []
        self.link_utilization_history: List[List[float]] = []
        self.active_path: List[int] = []

        # Record initial event
        self._record_event("SIMULATION_INITIALIZED", {
            "source": source,
            "destination": destination,
            "routing_method": routing_method,
            "dynamic_conditions": dynamic_conditions,
            "total_steps": total_steps
        })

    def _record_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Appends a timestamped verifiable simulation event."""
        self.events.append({
            "step": self.current_step,
            "timestamp_ms": round(time.time() * 1000.0, 1),
            "type": event_type,
            "details": details
        })

    def _get_link_id(self, u: int, v: int) -> Optional[str]:
        return self.link_endpoint_map.get((min(u, v), max(u, v)))

    def step(self) -> Dict[str, Any]:
        """Executes a single discrete simulation step."""
        if self.is_completed or self.current_step >= self.total_steps:
            self.is_completed = True
            return self.get_summary()

        step_idx = self.current_step
        demand_info = self.traffic_schedule[step_idx]
        offered_packets = demand_info["packets_offered"]
        is_burst = demand_info["is_burst"]

        # 1. Process dynamic events (link failures / recoveries)
        if step_idx in self.failure_schedule:
            event_spec = self.failure_schedule[step_idx]
            l_id = event_spec["link_id"]
            if l_id in self.links_by_id:
                link_obj = self.links_by_id[l_id]
                if event_spec["action"] == "fail":
                    link_obj["status"] = "failed"
                    self._record_event("LINK_FAILED", {
                        "link_id": l_id,
                        "source": link_obj["source"],
                        "target": link_obj["target"],
                        "reason": "Dynamic link fault injected"
                    })
                elif event_spec["action"] == "recover":
                    link_obj["status"] = "active"
                    self._record_event("LINK_RECOVERED", {
                        "link_id": l_id,
                        "source": link_obj["source"],
                        "target": link_obj["target"]
                    })

        if is_burst:
            self._record_event("TRAFFIC_BURST", {
                "packets_offered": offered_packets,
                "pattern": self.traffic_pattern
            })

        # 2. Compute route for current traffic flow
        route_info: Dict[str, Any] = {}
        route_path: List[int] = []
        success = False

        method = self.routing_method.lower()
        if method in ("ppo_shielded", "ppo+shield", "shielded_ppo", "ppo_residual+shield"):
            demand_hist = [
                s["packets_offered"] * 1500 * 8 / 1_000_000 / (settings.DEFAULT_STEP_DURATION_MS / 1000.0)
                for s in self.traffic_schedule[:step_idx + 1]
            ]
            route_info = self.candidate_agent.evaluate_route(
                nodes=self.nodes,
                links=self.links,
                source=self.source,
                destination=self.destination,
                link_endpoint_map=self.link_endpoint_map,
                links_by_id=self.links_by_id,
                util_history=self.link_utilization_history,
                demand_history=demand_hist,
                current_path=self.active_path,
                shielded=True
            )
            route_path = route_info.get("path", [])
            success = route_info.get("success", False)
            self.total_shield_evals += 1
            if route_info.get("shield_fallback"):
                self.shield_fallback_count += 1
                self._record_event("SHIELD_FALLBACK", {
                    "source": self.source,
                    "destination": self.destination,
                    "reason": "Policy candidate delay exceeded (1+tau)*CADJ bound",
                    "fallback_algorithm": "cadj"
                })
        elif method in ("ppo_residual", "ppo", "candidate_ppo", "residual_ppo"):
            demand_hist = [
                s["packets_offered"] * 1500 * 8 / 1_000_000 / (settings.DEFAULT_STEP_DURATION_MS / 1000.0)
                for s in self.traffic_schedule[:step_idx + 1]
            ]
            route_info = self.candidate_agent.evaluate_route(
                nodes=self.nodes,
                links=self.links,
                source=self.source,
                destination=self.destination,
                link_endpoint_map=self.link_endpoint_map,
                links_by_id=self.links_by_id,
                util_history=self.link_utilization_history,
                demand_history=demand_hist,
                current_path=self.active_path,
                shielded=False
            )
            route_path = route_info.get("path", [])
            success = route_info.get("success", False)
        elif "legacy" in method:
            # Per-hop legacy PPO
            env = NetworkRoutingEnv(
                nodes=self.nodes,
                links=self.links,
                source=self.source,
                destination=self.destination,
                max_hops=max(1, len(self.nodes) - 1)
            )
            route_info = self.ppo_agent.evaluate_route(env)
            route_path = route_info.get("path", [])
            success = route_info.get("success", False)
        else:
            # Traditional routing baseline (dijkstra_dynamic, dijkstra_static, least_loaded, cadj)
            route_info = TraditionalRouter.compute_route(
                nodes=self.nodes,
                links=self.links,
                source=self.source,
                destination=self.destination,
                algorithm=self.routing_method,
                previous_path=self.active_path
            )
            route_path = route_info.get("path", [])
            success = route_info.get("success", False)

        self.active_path = route_path

        # 3. Simulate packet transmission across path
        step_delivered = 0
        step_dropped = 0
        step_latencies: List[float] = []

        if success and len(route_path) >= 2:
            # Traverse path links and update utilization
            path_link_ids = []
            for i in range(len(route_path) - 1):
                lid = self._get_link_id(route_path[i], route_path[i + 1])
                if lid:
                    path_link_ids.append(lid)

            # Check if any link in path has failed
            has_failed_link = any(self.links_by_id[lid]["status"] == "failed" for lid in path_link_ids if lid in self.links_by_id)
            if has_failed_link:
                # All packets dropped due to broken link
                step_dropped = offered_packets
                self._record_event("PACKET_LOSS", {
                    "count": offered_packets,
                    "reason": "Path contains broken/failed link"
                })
            else:
                for _ in range(offered_packets):
                    # Compute per-packet latency through route
                    total_packet_delay = 0.0
                    packet_dropped = False

                    for lid in path_link_ids:
                        link_obj = self.links_by_id[lid]
                        cap = link_obj["capacity_mbps"]
                        current_q = link_obj.get("queue_occupancy", 0)

                        # The queue may be served during this simulation step.
                        # Allow packets up to service capacity + buffer before
                        # declaring overflow; the previous implementation used
                        # the buffer alone and dropped a burst even on an idle
                        # high-capacity link.
                        service_capacity_packets = int(
                            cap * 1_000_000
                            * (settings.DEFAULT_STEP_DURATION_MS / 1000.0)
                            / (1500 * 8)
                        )
                        queue_limit = service_capacity_packets + settings.BUFFER_SIZE_PACKETS
                        if current_q >= queue_limit:
                            packet_dropped = True
                            link_obj["packets_dropped"] = link_obj.get("packets_dropped", 0) + 1
                            break

                        # Increment link traffic
                        link_obj["queue_occupancy"] = current_q + 1
                        link_obj["packets_transmitted"] = link_obj.get("packets_transmitted", 0) + 1

                        # Compute dynamic delay
                        base_d = link_obj["base_delay_ms"]
                        util = link_obj.get("utilization", 0.1)
                        link_d = base_d / (1.0 - min(0.92, util))
                        total_packet_delay += link_d

                    if packet_dropped:
                        step_dropped += 1
                        self.packet_history.append({"delivered": False, "step": step_idx})
                    else:
                        step_delivered += 1
                        step_latencies.append(round(total_packet_delay, 2))
                        self.packet_history.append({
                            "delivered": True,
                            "latency_ms": round(total_packet_delay, 2),
                            "step": step_idx
                        })

                # Update utilization with consistent units. Each packet is
                # 1,500 bytes; offered load is converted to Mbps over this step.
                offered_mbps = (
                    offered_packets * 1500 * 8 / 1_000_000
                ) / (settings.DEFAULT_STEP_DURATION_MS / 1000.0)
                for lid in path_link_ids:
                    link_obj = self.links_by_id[lid]
                    load_fraction = min(0.95, offered_mbps / max(1e-9, link_obj["capacity_mbps"]))
                    new_util = 0.7 * link_obj["utilization"] + 0.3 * load_fraction
                    link_obj["utilization"] = round(new_util, 3)

                    if new_util >= settings.CONGESTION_UTILIZATION_THRESHOLD:
                        self._record_event("CONGESTION_SPIKE", {
                            "link_id": lid,
                            "utilization_pct": round(new_util * 100.0, 1),
                            "source": link_obj["source"],
                            "target": link_obj["target"]
                        })
        else:
            # No path found - packets cannot be routed
            step_dropped = offered_packets
            for _ in range(offered_packets):
                self.packet_history.append({"delivered": False, "step": step_idx, "reason": "No route available"})
            self._record_event("ROUTE_UNAVAILABLE", {
                "source": self.source,
                "destination": self.destination,
                "packets_dropped": offered_packets
            })

        # Record per-step utilization before decay so the final summary reports
        # the run's actual mean and peak, not only the cooled final snapshot.
        self.link_utilization_history.append([float(l.get("utilization", 0.0)) for l in self.links])

        # Drain queues according to the physical service capacity of each link.
        # The old fixed 25% decay caused queues to grow on unloaded links and
        # could manufacture packet drops unrelated to link bandwidth.
        step_seconds = settings.DEFAULT_STEP_DURATION_MS / 1000.0
        for link_obj in self.links:
            q = int(link_obj.get("queue_occupancy", 0))
            service_capacity_packets = int(
                float(link_obj.get("capacity_mbps", settings.DEFAULT_LINK_CAPACITY_MBPS))
                * 1_000_000 * step_seconds / (1500 * 8)
            )
            link_obj["queue_occupancy"] = max(0, q - service_capacity_packets)
            # Slowly cool off utilization between steps.
            link_obj["utilization"] = round(max(0.05, link_obj["utilization"] * 0.92), 3)

        # 4. Record step telemetry metrics
        step_avg_latency = float(sum(step_latencies) / len(step_latencies)) if step_latencies else 0.0
        step_metrics = {
            "step": step_idx,
            "packets_offered": offered_packets,
            "packets_delivered": step_delivered,
            "packets_dropped": step_dropped,
            "avg_latency_ms": round(step_avg_latency, 2),
            "route_hops": len(route_path) - 1 if route_path else 0,
            "route_path": route_path,
            "route_computation_time_ms": route_info.get("computation_time_ms", 0.0),
            "rl_reward": route_info.get("total_reward") if "ppo" in self.routing_method.lower() else None
        }
        self.step_metrics_timeline.append(step_metrics)

        self.current_step += 1
        if self.current_step >= self.total_steps:
            self.is_completed = True
            self._record_event("SIMULATION_COMPLETED", {
                "total_steps": self.total_steps,
                "delivered_total": sum(s["packets_delivered"] for s in self.step_metrics_timeline),
                "dropped_total": sum(s["packets_dropped"] for s in self.step_metrics_timeline)
            })

        return {
            "step": step_idx,
            "is_completed": self.is_completed,
            "step_metrics": step_metrics,
            "active_path": self.active_path,
            "events_emitted": [e for e in self.events if e["step"] == step_idx],
            "links_telemetry": [
                {
                    "id": l["id"],
                    "utilization": l["utilization"],
                    "status": l["status"],
                    "queue": l.get("queue_occupancy", 0)
                } for l in self.links
            ]
        }

    def run_all(self) -> Dict[str, Any]:
        """Runs the entire simulation synchronously."""
        while not self.is_completed:
            self.step()
        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Generates comprehensive final summary metrics and event log."""
        # Flatten every step's pre-decay link utilization. This avoids reporting
        # only the final cooled utilization and hiding earlier congestion spikes.
        all_utils = [u for snapshot in self.link_utilization_history for u in snapshot]
        if not all_utils:
            all_utils = [l["utilization"] for l in self.links]
        total_time_ms = self.total_steps * settings.DEFAULT_STEP_DURATION_MS
        
        # Calculate overall routing computation time average
        comp_times = [s["route_computation_time_ms"] for s in self.step_metrics_timeline if s["route_computation_time_ms"] > 0]
        avg_comp_time = float(sum(comp_times) / len(comp_times)) if comp_times else 0.0

        # RL rewards if applicable
        rl_rewards = [s["rl_reward"] for s in self.step_metrics_timeline if s["rl_reward"] is not None]
        avg_reward = float(sum(rl_rewards) / len(rl_rewards)) if rl_rewards else None

        final_metrics = compute_simulation_metrics(
            packet_records=self.packet_history,
            link_utilizations=all_utils,
            total_time_ms=total_time_ms,
            routing_computation_time_ms=avg_comp_time,
            rl_reward=avg_reward,
            shield_fallback_count=self.shield_fallback_count if self.total_shield_evals > 0 else None,
            shield_fallback_rate_pct=round((self.shield_fallback_count / self.total_shield_evals) * 100.0, 1) if self.total_shield_evals > 0 else None
        )

        return {
            "simulation_id": self.simulation_id,
            "is_completed": self.is_completed,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "routing_method": self.routing_method,
            "path": self.active_path.copy(),
            "metrics": final_metrics,
            "timeline": self.step_metrics_timeline,
            "events": self.events,
            "active_path": self.active_path,
            "topology_metadata": self.topology_data.get("metadata", {})
        }
