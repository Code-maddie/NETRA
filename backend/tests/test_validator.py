"""
Unit Tests for NETRA Network and Reachability Validator
"""
import pytest
from app.core.topology import generate_topology
from app.core.validator import NetworkValidator

def test_single_node_validation():
    topo = generate_topology(node_count=1)
    res = NetworkValidator.validate_network_and_endpoints(topo, source=0, destination=0)
    assert not res["valid"]
    assert res["is_single_node"] is True
    assert "Single-node network" in res["errors"][0]

def test_identical_endpoints_rejected():
    topo = generate_topology(node_count=10, topology_type="random")
    res = NetworkValidator.validate_network_and_endpoints(topo, source=3, destination=3)
    assert not res["valid"]
    assert "Source and destination must be distinct" in res["errors"][0]

def test_nonexistent_endpoints_rejected():
    topo = generate_topology(node_count=10, topology_type="random")
    res = NetworkValidator.validate_network_and_endpoints(topo, source=99, destination=2)
    assert not res["valid"]
    assert "Source node 99 does not exist" in res["errors"][0]

def test_valid_path_detection():
    topo = generate_topology(node_count=15, topology_type="line")
    res = NetworkValidator.validate_network_and_endpoints(topo, source=0, destination=14)
    assert res["valid"]
    assert res["details"]["path_exists"] is True
    assert res["details"]["min_hops"] == 14
