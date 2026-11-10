"""
Unit Tests for NETRA Topology Generation
Tests boundary conditions (1, 2, 685, 1000 nodes), invalid values, and graph properties.
"""
import pytest
from app.core.topology import generate_topology
from app.core.validator import NetworkValidator

def test_node_count_boundaries():
    # 1 Node (Special case)
    t1 = generate_topology(node_count=1, topology_type="random")
    assert len(t1["nodes"]) == 1
    assert len(t1["links"]) == 0
    assert t1["metadata"]["is_single_node"] is True

    # 2 Nodes (Minimal routable network)
    t2 = generate_topology(node_count=2, topology_type="line")
    assert len(t2["nodes"]) == 2
    assert len(t2["links"]) == 1

    # 685 Nodes (PRD Section 8 Reference Benchmark)
    t685 = generate_topology(node_count=685, topology_type="random", density="high", seed=42)
    assert len(t685["nodes"]) == 685
    assert len(t685["links"]) > 685
    assert t685["metadata"]["is_connected"] is True

    # 1000 Nodes (Maximum configured boundary)
    t1000 = generate_topology(node_count=1000, topology_type="random", density="medium", seed=99)
    assert len(t1000["nodes"]) == 1000
    assert len(t1000["links"]) >= 1000

def test_rejection_of_invalid_node_counts():
    # Rejection of 0
    with pytest.raises(ValueError):
        generate_topology(node_count=0)

    # Rejection of negative numbers
    with pytest.raises(ValueError):
        generate_topology(node_count=-5)

    # Rejection of values > 1000
    with pytest.raises(ValueError):
        generate_topology(node_count=1001)

    # Validator rejection
    v_zero = NetworkValidator.validate_configuration(node_count=0, topology_type="random")
    assert not v_zero["valid"]

    v_high = NetworkValidator.validate_configuration(node_count=1500, topology_type="random")
    assert not v_high["valid"]

    v_float = NetworkValidator.validate_configuration(node_count=25.5, topology_type="random")
    assert not v_float["valid"]

def test_supported_topologies():
    topologies = ["random", "scale_free", "mesh", "star", "ring", "line", "grid"]
    for topo in topologies:
        data = generate_topology(node_count=16, topology_type=topo, seed=42)
        assert len(data["nodes"]) == 16
        assert len(data["links"]) > 0
