"""
NETRA Scalable Network Topology Generator
Generates reproducible graph topologies from 1 to 1,000 nodes.
Calculates 2D spatial coordinates for rendering and assigns realistic link telemetry.
"""
import math
import random
from typing import Dict, Any, List, Optional
import networkx as nx

from app.config import settings

def _assign_link_properties(u: int, v: int, rng: random.Random) -> Dict[str, Any]:
    """Generates realistic physical link properties."""
    # Base delay between 2.0 ms and 20.0 ms
    base_delay = round(rng.uniform(2.5, 18.0), 2)
    # Capacity between 100 Mbps and 1000 Mbps
    capacity = float(rng.choice([100.0, 250.0, 500.0, 1000.0]))
    # Initial status and zero queue
    return {
        "id": f"{min(u, v)}-{max(u, v)}",
        "source": min(u, v),
        "target": max(u, v),
        "capacity_mbps": capacity,
        "base_delay_ms": base_delay,
        "current_delay_ms": base_delay,
        "utilization": round(rng.uniform(0.05, 0.25), 3),
        "status": "active",  # "active" or "failed"
        "loss_prob": 0.001,
        "weight": base_delay,
        "queue_occupancy": 0,
        "packets_transmitted": 0,
        "packets_dropped": 0
    }

def generate_topology(
    node_count: int,
    topology_type: str = "random",
    density: str = "medium",
    seed: Optional[int] = 42
) -> Dict[str, Any]:
    """
    Generates a network topology for NETRA.
    
    Parameters:
      node_count: Integer between 1 and 1000 inclusive.
      topology_type: 'random', 'mesh', 'star', 'ring', 'line', 'grid'.
      density: 'low', 'medium', 'high' (used for random topology).
      seed: Random seed for reproducibility.
      
    Returns:
      Dictionary containing nodes, links, and topology metadata.
    """
    if node_count < settings.MIN_NODES or node_count > settings.MAX_NODES:
        raise ValueError(f"Node count must be between {settings.MIN_NODES} and {settings.MAX_NODES}. Received: {node_count}")

    topology_type = topology_type.lower()
    if topology_type not in settings.SUPPORTED_TOPOLOGIES:
        raise ValueError(f"Unsupported topology: {topology_type}. Supported: {settings.SUPPORTED_TOPOLOGIES}")

    rng = random.Random(seed)
    G = nx.Graph()

    # Special Case: Single node network
    if node_count == 1:
        G.add_node(0, x=500.0, y=500.0, label="Node 0")
        return {
            "metadata": {
                "node_count": 1,
                "link_count": 0,
                "topology_type": topology_type,
                "density": density,
                "seed": seed,
                "is_connected": True,
                "is_single_node": True
            },
            "nodes": [{"id": 0, "label": "Node 0", "x": 500.0, "y": 500.0, "degree": 0}],
            "links": []
        }

    # Generate graph structure based on topology type
    if topology_type == "star":
        # Node 0 is center hub, connects to 1..node_count-1
        G.add_node(0, x=500.0, y=500.0)
        radius = 380.0
        for i in range(1, node_count):
            angle = (2.0 * math.pi * (i - 1)) / (node_count - 1)
            x = 500.0 + radius * math.cos(angle)
            y = 500.0 + radius * math.sin(angle)
            G.add_node(i, x=round(x, 2), y=round(y, 2))
            G.add_edge(0, i)

    elif topology_type == "ring":
        # Circular ring layout
        radius = 400.0
        for i in range(node_count):
            angle = (2.0 * math.pi * i) / node_count
            x = 500.0 + radius * math.cos(angle)
            y = 500.0 + radius * math.sin(angle)
            G.add_node(i, x=round(x, 2), y=round(y, 2))
            G.add_edge(i, (i + 1) % node_count)

    elif topology_type == "line":
        # Linear bus topology
        for i in range(node_count):
            x = 60.0 + (880.0 * i) / max(1, node_count - 1)
            # Add slight sinusoidal wave so nodes don't overlap completely on a single flat line
            y = 500.0 + 80.0 * math.sin(i * 0.35)
            G.add_node(i, x=round(x, 2), y=round(y, 2))
            if i > 0:
                G.add_edge(i - 1, i)

    elif topology_type == "mesh":
        # Full mesh for small graphs, dense chordal mesh for larger graphs to maintain scalability
        radius = 420.0
        for i in range(node_count):
            angle = (2.0 * math.pi * i) / node_count
            x = 500.0 + radius * math.cos(angle)
            y = 500.0 + radius * math.sin(angle)
            G.add_node(i, x=round(x, 2), y=round(y, 2))

        if node_count <= 40:
            # Complete mesh K_n
            for i in range(node_count):
                for j in range(i + 1, node_count):
                    G.add_edge(i, j)
        else:
            # Scaled mesh: k nearest neighbors + random long-range chords
            k_neighbors = min(8, node_count // 4)
            for i in range(node_count):
                for offset in range(1, k_neighbors + 1):
                    G.add_edge(i, (i + offset) % node_count)
            # Add chords
            num_chords = min(node_count * 2, 2500)
            for _ in range(num_chords):
                u = rng.randint(0, node_count - 1)
                v = rng.randint(0, node_count - 1)
                if u != v:
                    G.add_edge(u, v)

    elif topology_type == "grid":
        # 2D Grid lattice
        cols = math.ceil(math.sqrt(node_count))
        rows = math.ceil(node_count / cols)
        dx = 800.0 / max(1, cols - 1) if cols > 1 else 0
        dy = 800.0 / max(1, rows - 1) if rows > 1 else 0

        for i in range(node_count):
            r = i // cols
            c = i % cols
            x = 100.0 + c * dx
            y = 100.0 + r * dy
            G.add_node(i, x=round(x, 2), y=round(y, 2))
            # Connect horizontal neighbor
            if c > 0 and (i - 1) < node_count:
                G.add_edge(i - 1, i)
            # Connect vertical neighbor
            if r > 0 and (i - cols) < node_count:
                G.add_edge(i - cols, i)

    else:  # "random" and "scale_free" topologies
        # Connected random geometric or Barabasi-Albert/Watts-Strogatz graph
        density_multipliers = {
            "low": 2,
            "medium": 4,
            "high": 7
        }
        m = density_multipliers.get(density.lower(), 4)
        m = min(m, max(1, node_count - 1))

        # Generate connected Barabasi-Albert graph or Erdos-Renyi
        if node_count <= m:
            G = nx.complete_graph(node_count)
        else:
            G = nx.barabasi_albert_graph(node_count, m, seed=seed)

        # In case user requested high density, add additional random shortcut links
        if density == "high" and node_count > 10:
            extra_edges = min(node_count * 3, 3000)
            nodes_list = list(G.nodes())
            for _ in range(extra_edges):
                u = rng.choice(nodes_list)
                v = rng.choice(nodes_list)
                if u != v:
                    G.add_edge(u, v)

        # Calculate high-performance 2D layout coordinates
        # For small-medium graphs, use spring layout; for large graphs (up to 1,000), use fast hierarchical/spectral or concentric distribution
        if node_count <= 250:
            pos = nx.spring_layout(G, seed=seed, iterations=35)
        else:
            # Scalable fast deterministic placement for large graphs (685 and 1000 nodes)
            pos = {}
            num_clusters = max(5, int(math.sqrt(node_count) / 1.5))
            cluster_centers = []
            for c_idx in range(num_clusters):
                c_angle = (2.0 * math.pi * c_idx) / num_clusters
                c_dist = rng.uniform(120.0, 360.0)
                cluster_centers.append((500.0 + c_dist * math.cos(c_angle), 500.0 + c_dist * math.sin(c_angle)))
            
            for node_id in G.nodes():
                # Assign to cluster with jitter
                c_x, c_y = cluster_centers[node_id % num_clusters]
                jitter_r = rng.uniform(5.0, 95.0)
                jitter_a = rng.uniform(0, 2.0 * math.pi)
                pos[node_id] = (
                    (c_x + jitter_r * math.cos(jitter_a) - 500.0) / 450.0,
                    (c_y + jitter_r * math.sin(jitter_a) - 500.0) / 450.0
                )

        # Scale coordinates into [60, 940] range
        for node_id in G.nodes():
            raw_x, raw_y = pos[node_id]
            x_coord = 500.0 + raw_x * 420.0
            y_coord = 500.0 + raw_y * 420.0
            G.nodes[node_id]["x"] = round(max(50.0, min(950.0, x_coord)), 2)
            G.nodes[node_id]["y"] = round(max(50.0, min(950.0, y_coord)), 2)

    # Format nodes payload
    nodes_payload = []
    for node_id in sorted(G.nodes()):
        attrs = G.nodes[node_id]
        nodes_payload.append({
            "id": int(node_id),
            "label": f"Node {node_id}",
            "x": attrs.get("x", 500.0),
            "y": attrs.get("y", 500.0),
            "degree": int(G.degree[node_id])
        })

    # Format links payload with telemetry attributes
    links_payload = []
    seen_links = set()
    for u, v in G.edges():
        u_int, v_int = int(u), int(v)
        link_key = (min(u_int, v_int), max(u_int, v_int))
        if link_key not in seen_links:
            seen_links.add(link_key)
            props = _assign_link_properties(u_int, v_int, rng)
            links_payload.append(props)

    is_connected = nx.is_connected(G) if node_count > 1 else True

    return {
        "metadata": {
            "node_count": node_count,
            "link_count": len(links_payload),
            "topology_type": topology_type,
            "density": density,
            "seed": seed,
            "is_connected": is_connected,
            "is_single_node": False,
            "connected_components": nx.number_connected_components(G) if node_count > 1 else 1,
            "average_degree": round(2.0 * len(links_payload) / max(1, node_count), 2)
        },
        "nodes": nodes_payload,
        "links": links_payload
    }
