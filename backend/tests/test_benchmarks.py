"""
Performance Benchmark Suite for NETRA
Tests scale performance for 50, 245, 685, and 1,000 nodes.
"""
import time
import pytest
from app.core.topology import generate_topology
from app.core.traditional_routing import TraditionalRouter

@pytest.mark.parametrize("node_count", [50, 245, 685, 1000])
def test_topology_scale_generation(node_count):
    start = time.perf_counter()
    density = "high" if node_count == 685 else "medium"
    topo = generate_topology(node_count=node_count, topology_type="random", density=density, seed=42)
    elapsed = time.perf_counter() - start

    assert len(topo["nodes"]) == node_count
    # Generation must complete within 2.5 seconds even for 1,000 nodes
    assert elapsed < 2.5, f"Generation of {node_count} nodes took {elapsed:.2f}s, expected < 2.5s"

    # Verify routing calculation speed on large graphs
    route_start = time.perf_counter()
    res = TraditionalRouter.compute_route(
        nodes=topo["nodes"],
        links=topo["links"],
        source=0,
        destination=node_count - 1
    )
    route_elapsed = time.perf_counter() - route_start
    assert route_elapsed < 1.0, f"Routing on {node_count} nodes took {route_elapsed:.2f}s, expected < 1.0s"
