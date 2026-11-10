"""
Unit Tests for NETRA Dynamic Simulation Engine
"""
import pytest
from app.core.topology import generate_topology
from app.core.simulator import NetworkSimulator

def test_dynamic_simulation_execution():
    topo = generate_topology(node_count=20, topology_type="random", density="medium", seed=42)
    sim = NetworkSimulator(
        topology_data=topo,
        source=0,
        destination=15,
        routing_method="dijkstra_dynamic",
        traffic_pattern="mixed",
        dynamic_conditions=True,
        total_steps=12,
        seed=42
    )
    
    # Run simulation
    summary = sim.run_all()
    assert summary["is_completed"] is True
    assert summary["total_steps"] == 12
    assert len(summary["timeline"]) == 12
    assert len(summary["events"]) > 0
    assert summary["metrics"]["packets_offered"] > 0


def test_simulator_reports_route_and_historical_utilization():
    topo = generate_topology(node_count=2, topology_type="line", seed=3)
    topo["links"][0]["capacity_mbps"] = 100.0
    topo["links"][0]["utilization"] = 0.0
    sim = NetworkSimulator(
        topology_data=topo,
        source=0,
        destination=1,
        routing_method="dijkstra_dynamic",
        traffic_pattern="constant",
        dynamic_conditions=False,
        total_steps=2,
        seed=3,
    )
    summary = sim.run_all()
    assert summary["path"] == [0, 1]
    # One 1,500-byte packet is 12,000 bits; 2,500 packets in 0.5 s are ~60 Mbps.
    # With a 100 Mbps link, the first pre-decay sample is about 18% utilization
    # under the simulator's 0.3 moving-average update (not 95% from bad units).
    assert 0.0 < summary["metrics"]["max_link_utilization_pct"] < 40.0
