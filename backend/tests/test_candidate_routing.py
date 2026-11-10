"""
Unit and Integration Tests for Candidate-Path Residual PPO and Shielding.
"""
import pytest
import numpy as np
import networkx as nx
import torch

from app.core.topology import generate_topology
from app.core.traditional_routing import TraditionalRouter
from app.core.rl.candidate_agent import CandidatePolicy, CandidatePPOAgent, K_CANDIDATES, N_FEATURES
from app.core.simulator import NetworkSimulator
from app.core.metrics import compute_simulation_metrics, compare_routing_results


def test_candidate_paths_generation():
    topo = generate_topology(node_count=12, topology_type="random", density="medium", seed=42)
    candidates = TraditionalRouter.get_candidate_paths(topo["nodes"], topo["links"], source=0, destination=11, k=K_CANDIDATES)
    
    assert len(candidates) > 0
    assert len(candidates) <= K_CANDIDATES
    # Candidate 0 must match static Dijkstra shortest path
    static_route = TraditionalRouter.compute_route(topo["nodes"], topo["links"], source=0, destination=11, algorithm="dijkstra_static")
    assert candidates[0] == static_route["path"]


def test_candidate_policy_forward():
    policy = CandidatePolicy(d=N_FEATURES, h=64)
    batch_size = 2
    nf_flows = 8
    
    # Multi-flow input (batch, NF, K, 13)
    x = torch.randn(batch_size, nf_flows, K_CANDIDATES, N_FEATURES)
    m = torch.ones(batch_size, nf_flows, K_CANDIDATES, dtype=torch.bool)
    m[:, :, 2:] = False  # Mask out candidate 2 and 3
    
    lg, val = policy(x, m)
    assert lg.shape == (batch_size, nf_flows, K_CANDIDATES)
    assert val.shape == (batch_size,)
    # Masked positions should have large negative logits
    assert (lg[:, :, 2:] < -1e8).all()

    # Single-flow input (batch, K, 13)
    x_single = torch.randn(batch_size, K_CANDIDATES, N_FEATURES)
    m_single = torch.ones(batch_size, K_CANDIDATES, dtype=torch.bool)
    lg_s, val_s = policy(x_single, m_single)
    assert lg_s.shape == (batch_size, K_CANDIDATES)
    assert val_s.shape == (batch_size,)


def test_cadj_routing_with_hysteresis():
    topo = generate_topology(node_count=8, topology_type="ring", seed=42)
    # First step without previous path
    res1 = TraditionalRouter.compute_route(topo["nodes"], topo["links"], source=0, destination=4, algorithm="cadj")
    assert res1["success"] is True
    assert len(res1["path"]) >= 2
    
    # Second step with previous path (stickiness prevents oscillation)
    res2 = TraditionalRouter.compute_route(
        topo["nodes"], topo["links"], source=0, destination=4, algorithm="cadj", previous_path=res1["path"]
    )
    assert res2["success"] is True
    assert res2["path"] == res1["path"]


def test_candidate_agent_feature_extraction():
    topo = generate_topology(node_count=10, topology_type="random", density="medium", seed=42)
    agent = CandidatePPOAgent()
    
    candidates = TraditionalRouter.get_candidate_paths(topo["nodes"], topo["links"], source=0, destination=9, k=4)
    endpoint_map = {(min(l["source"], l["target"]), max(l["source"], l["target"])): l["id"] for l in topo["links"]}
    links_by_id = {l["id"]: l for l in topo["links"]}
    
    F, mask = agent.extract_features(
        nodes=topo["nodes"],
        links=topo["links"],
        candidate_paths=candidates,
        link_endpoint_map=endpoint_map,
        links_by_id=links_by_id,
        util_history=[[0.2]*len(topo["links"])],
        demand_history=[60.0]
    )
    
    assert F.shape == (4, N_FEATURES)
    assert mask.shape == (4,)
    assert mask.any()
    # Check bounded values
    assert (F[:, 6] >= 0).all()  # hop feature


def test_candidate_shielding_evaluation():
    topo = generate_topology(node_count=10, topology_type="random", density="medium", seed=42)
    agent = CandidatePPOAgent()
    endpoint_map = {(min(l["source"], l["target"]), max(l["source"], l["target"])): l["id"] for l in topo["links"]}
    links_by_id = {l["id"]: l for l in topo["links"]}
    
    route = agent.evaluate_route(
        nodes=topo["nodes"],
        links=topo["links"],
        source=0,
        destination=9,
        link_endpoint_map=endpoint_map,
        links_by_id=links_by_id,
        util_history=[],
        demand_history=[],
        shielded=True,
        tau=0.05
    )
    
    assert route["success"] is True
    assert len(route["path"]) >= 2
    assert "shield_fallback" in route
    assert "candidate_index" in route


def test_simulator_with_candidate_and_shielded_ppo():
    topo = generate_topology(node_count=15, topology_type="random", density="medium", seed=42)
    
    # 1. Test unshielded residual PPO
    sim_res = NetworkSimulator(
        topology_data=topo,
        source=0,
        destination=14,
        routing_method="ppo_residual",
        traffic_pattern="mixed",
        dynamic_conditions=True,
        total_steps=10,
        seed=42
    )
    res_summary = sim_res.run_all()
    assert res_summary["is_completed"] is True
    assert res_summary["metrics"]["packets_delivered"] > 0
    assert res_summary["metrics"]["packet_loss_pct"] < 50.0

    # 2. Test shielded residual PPO
    sim_shield = NetworkSimulator(
        topology_data=topo,
        source=0,
        destination=14,
        routing_method="ppo_shielded",
        traffic_pattern="bursty",
        dynamic_conditions=True,
        total_steps=10,
        seed=42
    )
    shield_summary = sim_shield.run_all()
    assert shield_summary["is_completed"] is True
    assert shield_summary["metrics"]["packets_delivered"] > 0
    assert "shield_fallback_count" in shield_summary["metrics"]
    assert "shield_fallback_rate_pct" in shield_summary["metrics"]


def test_simulator_with_cadj():
    topo = generate_topology(node_count=15, topology_type="random", density="medium", seed=42)
    sim_cadj = NetworkSimulator(
        topology_data=topo,
        source=0,
        destination=14,
        routing_method="cadj",
        traffic_pattern="mixed",
        dynamic_conditions=True,
        total_steps=10,
        seed=42
    )
    cadj_summary = sim_cadj.run_all()
    assert cadj_summary["is_completed"] is True
    assert cadj_summary["metrics"]["packets_delivered"] > 0
