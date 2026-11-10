"""
Unit Tests for Routing Algorithms (Dijkstra and PPO RL) and Metrics Engine
"""
import pytest
from app.core.topology import generate_topology
from app.core.traditional_routing import TraditionalRouter
from app.core.rl.environment import NetworkRoutingEnv
from app.core.rl.ppo_agent import PPOAgent
from app.core.metrics import compute_simulation_metrics, compare_routing_results

def test_dijkstra_shortest_path():
    topo = generate_topology(node_count=10, topology_type="line")
    route = TraditionalRouter.compute_route(
        nodes=topo["nodes"],
        links=topo["links"],
        source=0,
        destination=9,
        algorithm="dijkstra_dynamic"
    )
    assert route["success"] is True
    assert route["path"] == list(range(10))
    assert route["hops"] == 9
    assert route["computation_time_ms"] >= 0.0


def test_capacity_aware_and_ecmp_routes_are_valid():
    topo = generate_topology(node_count=10, topology_type="ring")
    for algorithm in ("capacity_aware", "ecmp"):
        route = TraditionalRouter.compute_route(
            topo["nodes"], topo["links"], 0, 5, algorithm=algorithm
        )
        assert route["success"] is True
        assert route["path"][0] == 0
        assert route["path"][-1] == 5

def test_ppo_environment_and_masking():
    topo = generate_topology(node_count=8, topology_type="ring")
    env = NetworkRoutingEnv(topo["nodes"], topo["links"], source=0, destination=4)
    obs = env.reset()
    assert len(obs) == env.state_dim

    mask = env.get_action_mask()
    assert mask.any()
    
    agent = PPOAgent()
    route_res = agent.evaluate_route(env, max_hops=20)
    assert "path" in route_res
    assert route_res["computation_time_ms"] >= 0.0

def test_metrics_calculation_and_honest_comparison():
    # Synthetic packet test
    packets = [
        {"delivered": True, "latency_ms": 12.0},
        {"delivered": True, "latency_ms": 16.0},
        {"delivered": False}
    ]
    metrics = compute_simulation_metrics(packets, [0.4, 0.6], total_time_ms=1000.0)
    assert metrics["packets_offered"] == 3
    assert metrics["packets_delivered"] == 2
    assert metrics["packets_dropped"] == 1
    assert metrics["delivery_success_rate_pct"] == round(2/3 * 100, 2)
    assert metrics["packet_loss_pct"] == round(1/3 * 100, 2)
    assert metrics["avg_latency_ms"] == 14.0

    # Comparison test
    res_a = {"algorithm": "Dijkstra", "metrics": metrics, "path": [0, 1, 2]}
    res_b = {"algorithm": "PPO", "metrics": {**metrics, "avg_latency_ms": 10.0}, "path": [0, 3, 2]}
    comp = compare_routing_results(res_a, res_b)
    assert "winner" in comp
    assert "improvements" in comp


def test_rl_route_avoids_cycles_and_reaches_destination_on_line_topology():
    """A random policy should not get stuck in loops when only one route exists."""
    topo = generate_topology(node_count=12, topology_type="line", seed=17)
    env = NetworkRoutingEnv(topo["nodes"], topo["links"], source=0, destination=11, max_hops=20)
    result = PPOAgent().evaluate_route(env, max_hops=20)
    assert result["success"] is True
    assert result["path"] == list(range(12))
    assert len(result["path"]) == len(set(result["path"]))


def test_comparison_does_not_treat_zero_deliveries_as_zero_latency_win():
    traditional = {
        "routing_method": "dijkstra_dynamic",
        "path": [0, 1, 2],
        "metrics": {
            "packets_delivered": 100,
            "packets_dropped": 0,
            "packet_loss_pct": 0.0,
            "avg_latency_ms": 12.0,
            "throughput_mbps": 1.2,
            "routing_computation_time_ms": 0.2,
        },
    }
    rl = {
        "routing_method": "ppo",
        "path": [0, 2, 0],
        "metrics": {
            "packets_delivered": 0,
            "packets_dropped": 100,
            "packet_loss_pct": 100.0,
            "avg_latency_ms": 0.0,
            "throughput_mbps": 0.0,
            "routing_computation_time_ms": 1.5,
        },
    }
    comp = compare_routing_results(traditional, rl)
    assert comp["latency_comparable"] is False
    assert comp["improvements"]["latency_improvement_pct"] is None
    assert not any("100.0% lower average latency" in reason for reason in comp["reasons"])
    assert comp["winner"] == "Traditional Routing (Dijkstra)"
    assert comp["side_by_side"]["traditional"]["path"] == [0, 1, 2]


def test_only_versioned_checkpoint_is_reported_as_trained(tmp_path, monkeypatch):
    import torch
    from app.config import settings

    isolated_weights = tmp_path / "weights"
    isolated_weights.mkdir()
    monkeypatch.setattr(settings, "MODEL_WEIGHTS_DIR", isolated_weights)

    legacy_path = tmp_path / "legacy.pt"
    torch.save(PPOAgent().policy.state_dict(), legacy_path)
    agent = PPOAgent()
    assert agent.load_checkpoint(str(legacy_path)) is False
    assert agent.trained is False

    versioned_path = tmp_path / "trained.pt"
    agent.save_checkpoint(str(versioned_path), trained=True, training_episodes=25)
    reloaded = PPOAgent()
    assert reloaded.load_checkpoint(str(versioned_path)) is True
    assert reloaded.trained is True
    assert reloaded.training_episodes == 25


def test_rl_action_mask_keeps_costly_but_viable_routes_available():
    nodes = [{"id": i} for i in range(4)]
    links = [
        {"id": "0-1", "source": 0, "target": 1, "base_delay_ms": 1.0, "utilization": 0.0, "status": "active"},
        {"id": "1-3", "source": 1, "target": 3, "base_delay_ms": 1.0, "utilization": 0.0, "status": "active"},
        {"id": "0-2", "source": 0, "target": 2, "base_delay_ms": 30.0, "utilization": 0.0, "status": "active"},
        {"id": "2-3", "source": 2, "target": 3, "base_delay_ms": 30.0, "utilization": 0.0, "status": "active"},
    ]
    env = NetworkRoutingEnv(nodes, links, source=0, destination=3)
    env.reset()
    assert env.get_action_mask().sum() == 2


def test_comparison_counts_material_routing_computation_overhead():
    shared_metrics = {
        "packets_delivered": 100,
        "packets_dropped": 0,
        "packet_loss_pct": 0.0,
        "avg_latency_ms": 12.0,
        "throughput_mbps": 1.2,
    }
    traditional = {"path": [0, 1], "metrics": {**shared_metrics, "routing_computation_time_ms": 0.2}}
    rl = {"path": [0, 1], "metrics": {**shared_metrics, "routing_computation_time_ms": 1.2}}
    comparison = compare_routing_results(traditional, rl)
    assert comparison["winner"] == "Traditional Routing (Dijkstra)"
    assert any("RL routing computation took longer" in reason for reason in comparison["reasons"])
