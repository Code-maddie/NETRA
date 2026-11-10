"""
NETRA Topology API Endpoints
Handles topology generation, validation, and reference configurations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from app.config import settings
from app.core.topology import generate_topology
from app.core.validator import NetworkValidator

router = APIRouter(prefix="/topology", tags=["Topology"])

class GenerateTopologyRequest(BaseModel):
    node_count: int = Field(default=20, description="Node count between 1 and 1000")
    topology_type: str = Field(default="random", description="random, mesh, star, ring, line, grid")
    density: str = Field(default="medium", description="low, medium, high")
    seed: Optional[int] = Field(default=42, description="Random seed")

class ValidateEndpointsRequest(BaseModel):
    topology_data: Dict[str, Any]
    source: Optional[int] = None
    destination: Optional[int] = None

@router.post("/generate")
def api_generate_topology(req: GenerateTopologyRequest):
    """Generates a network topology for NETRA."""
    # Pre-validate configuration bounds
    val_res = NetworkValidator.validate_configuration(
        node_count=req.node_count,
        topology_type=req.topology_type,
        density=req.density
    )
    if not val_res["valid"]:
        raise HTTPException(status_code=400, detail={"errors": val_res["errors"], "warnings": val_res["warnings"]})

    try:
        topo = generate_topology(
            node_count=req.node_count,
            topology_type=req.topology_type,
            density=req.density,
            seed=req.seed
        )
        return {
            "success": True,
            "data": topo,
            "warnings": val_res["warnings"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate topology: {str(e)}")

@router.post("/demo/burst-congestion")
def api_burst_congestion_demo():
    """Return a deterministic two-route topology for the PPO burst-congestion demo."""
    nodes = [
        {"id": 0, "label": "Source", "x": 100.0, "y": 500.0, "degree": 2},
        {"id": 1, "label": "Short Route A", "x": 330.0, "y": 350.0, "degree": 2},
        {"id": 2, "label": "Alternate B1", "x": 330.0, "y": 700.0, "degree": 2},
        {"id": 3, "label": "Alternate B2", "x": 670.0, "y": 700.0, "degree": 2},
        {"id": 4, "label": "Destination", "x": 900.0, "y": 500.0, "degree": 2},
    ]
    edge_specs = [
        (0, 1, 5.0, 1000.0), (1, 4, 5.0, 100.0),
        (0, 2, 4.0, 1000.0), (2, 3, 4.0, 1000.0), (3, 4, 4.0, 1000.0),
    ]
    links = []
    for source, target, delay, capacity in edge_specs:
        links.append({
            "id": f"{source}-{target}", "source": source, "target": target,
            "capacity_mbps": capacity, "base_delay_ms": delay,
            "current_delay_ms": delay, "utilization": 0.05, "status": "active",
            "loss_prob": 0.0, "weight": delay, "queue_occupancy": 0,
            "packets_transmitted": 0, "packets_dropped": 0,
        })
    return {
        "success": True,
        "data": {
            "metadata": {
                "node_count": len(nodes), "link_count": len(links),
                "topology_type": "burst_congestion_demo", "density": "custom",
                "seed": 42, "is_connected": True,
                "description": "Two-hop shortest route has a 100 Mbps bottleneck; the three-hop alternate has 1 Gbps links.",
            },
            "nodes": nodes,
            "links": links,
        },
        "warnings": [],
    }

@router.post("/validate")
def api_validate_network(req: ValidateEndpointsRequest):
    """Validates network connectivity and source-destination reachability."""
    result = NetworkValidator.validate_network_and_endpoints(
        topology_data=req.topology_data,
        source=req.source,
        destination=req.destination
    )
    return result

@router.get("/presets")
def api_get_presets():
    """Returns official reference configurations including PRD Section 8 reference benchmark."""
    return {
        "benchmark_reference": {
            "name": "PRD Reference Benchmark (685 Nodes)",
            "description": "Initial reference configuration from PRD Section 8",
            "node_count": settings.BENCHMARK_NODES,
            "topology_type": settings.BENCHMARK_TOPOLOGY,
            "density": settings.BENCHMARK_DENSITY,
            "source": settings.BENCHMARK_SOURCE,
            "destination": settings.BENCHMARK_DESTINATION,
            "traffic_pattern": settings.BENCHMARK_TRAFFIC,
            "dynamic_conditions": True,
            "seed": 42
        },
        "max_benchmark": {
            "name": "Max Scale Stress Test (1,000 Nodes)",
            "description": "Full-scale 1,000-node stress test",
            "node_count": settings.MAX_NODES,
            "topology_type": "random",
            "density": "medium",
            "source": 1,
            "destination": 900,
            "traffic_pattern": "mixed",
            "dynamic_conditions": True,
            "seed": 99
        },
        "classroom_demo": {
            "name": "Classroom Quick Demo (25 Nodes)",
            "description": "Rapid demo showing clear path rerouting and traffic bursts",
            "node_count": 25,
            "topology_type": "random",
            "density": "high",
            "source": 0,
            "destination": 24,
            "traffic_pattern": "bursty",
            "dynamic_conditions": True,
            "seed": 101
        },
        "single_node_test": {
            "name": "Boundary Test: 1 Node",
            "description": "Special boundary case demonstrating single-node validation",
            "node_count": 1,
            "topology_type": "random",
            "density": "low",
            "source": 0,
            "destination": 0,
            "traffic_pattern": "constant",
            "dynamic_conditions": False,
            "seed": 1
        }
    }
