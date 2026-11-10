# NETRA: Network Engineering, Traffic Routing & Intelligence Platform

NETRA is an interactive network simulation and routing intelligence platform that compares traditional routing algorithms (Dijkstra, Least-Loaded) with Reinforcement Learning (Proximal Policy Optimization - PPO) under dynamic conditions.

## NETRA V3 capabilities

- Variable networks from 1 to 1,000 nodes across random, scale-free, mesh, star, ring, line, and grid topologies.
- Integrated discrete-event packet simulation with constant, bursty, random-burst, periodic, and mixed traffic.
- Static Dijkstra, delay-sensitive routing, least-loaded routing, capacity-aware routing, ECMP, and CADJ hysteresis routing.
- Paired conventional routing, link-weight optimization, legacy PPO, candidate imitation policy, residual PPO, and shielded PPO evaluation.
- Graph-aware candidate routing observations, DAgger imitation initialization, validation-selected PPO checkpoints, safety fallback, and hysteresis.
- REST APIs and WebSocket playback for topology, simulation, optimization, RL, routing comparison, and experiment storage.

---

## 🌟 Key Features

1. **Configurable Topology Builder (1 to 1,000 Nodes)**
   - Granular slider & direct numeric input covering all integer values from 1 to 1,000.
   - Topologies: Random (Barabási–Albert scale-free), Mesh, Star, Ring, Line, and Grid.
   - Connection density options: Low, Medium, and High.
   - Special single-node handling and boundary validation.
   - 1-click **PRD Section 8 Reference Benchmark (685 nodes)** preset.

2. **Dynamic Discrete-Event Simulation Engine**
   - Step-by-step traffic demands: Constant, Bursty, Periodic, and Mixed traffic.
   - Dynamic network faults: Mid-simulation link failures and automated link recoveries.
   - Buffer queue simulation: Packet drop tracking and congestion detection ($U \ge 80\%$).
   - Verifiable event logger: Emits real timestamped events (`SIMULATION_INITIALIZED`, `LINK_FAILED`, `LINK_RECOVERED`, `CONGESTION_SPIKE`, `TRAFFIC_BURST`, `PACKET_LOSS`, `SIMULATION_COMPLETED`).

3. **Reinforcement Learning (PPO V2) vs Traditional Routing**
   - **Candidate-Path Decision Space**: Solves looping and sparse per-hop rewards by evaluating $K=4$ precomputed loop-free candidate paths (candidate 0 = static Dijkstra).
   - **Topology-Agnostic Shared Scorer MLP**: Uses 13 normalized path features ($U_{t-1}, U_{t-2}, U_{t-3}$, projected utilization, delay ratio, hop count, bottleneck capacity, hysteresis stickiness, demand trends, mean network load) to score candidate paths on any topology size.
   - **DAgger Imitation Pre-Training**: Pre-trains from a privileged teacher to eliminate random cold-starts.
   - **Residual PPO with KL Regularization**: Clones the BC policy and optimizes with clipped surrogate loss, value estimation, and a KL penalty toward the cloned policy using relative rewards against the shadow baseline (CADJ).
   - **Provable Safety Shielding**: Verifies candidate cost against the hysteresis baseline at runtime. If the policy exceeds $(1+\tau) \times \text{baseline cost}$, it falls back safely to CADJ and reports fallback telemetry.
   - **CADJ Baseline**: Hysteresis delay-sensitive routing that suppresses route flapping and oscillation.
   - **Legacy Per-Hop PPO**: Preserved for historical comparison and diagnosis.
   - **Honest Comparative Evaluation**: Paired scenario metrics, bootstrap confidence intervals, W/T/L tracking, and delivery/loss/throughput telemetry. Zero delivery is never treated as zero latency.

4. **Scalable Graph Visualization**
   - High-performance HTML5 Canvas renderer capable of rendering up to 1,000 nodes at 60 FPS.
   - Pan, zoom, node selection, edge inspection, and animated packet flow pulses.
   - Adaptive level-of-detail (LOD) labeling to prevent visual clutter at scale.

5. **Experiment History & Audit Ledger**
   - Persistent ledger storing run configurations, telemetry timelines, and reproducible seeds.
   - Search, filter, inspect, and delete experiment runs.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (with `torch`, `fastapi`, `uvicorn`, `networkx`, `numpy`)
- Node.js 18+ and `npm`

### 1. First-time setup and launch

The source ZIP intentionally does not bundle platform-specific `node_modules`, compiled `dist` output, or a previously saved PPO checkpoint. Python 3.10+ and Node.js 18+ are required. From the extracted project folder, install dependencies once, then launch the services:

```bash
python3 -m pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
bash ./run_all.sh
```

The launcher checks that both dependency sets are installed and waits for the backend health endpoint before starting the frontend. It does not terminate other programs using ports 8000 or 3000. If either port is already in use, stop that program or change the port in the backend launch command and `frontend/vite.config.js` before retrying.

If the dashboard opens but reports that it could not load the network, the frontend is reachable and the backend is not responding. Check the terminal for the backend startup error; install/update backend dependencies with `python3 -m pip install -r backend/requirements.txt`, then restart the launcher. The UI also provides a Retry button after the backend is available.

This automatically launches:
- **FastAPI Backend**: `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)
- **Vite React Frontend**: `http://localhost:3000`

### 2. Manual Startup

**Backend:**
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing and Benchmarks

Run the test suite:
```bash
cd backend
python3 -m pytest tests -v
```

### Benchmark Results and Interpretation

Do not treat historical timing figures as machine-independent guarantees. Routing runtime depends on hardware, topology density, node count, installed dependencies, and whether the algorithm is running a neural policy or a graph search. Re-run the same workload with the same seed and configuration when collecting project evidence.

For a fair comparison, train PPO on the selected topology, use identical traffic settings and seed for each method, repeat across multiple seeds (preferably 5–10 or more), and report mean and variability for every metric. When link costs are static, Dijkstra is an optimal shortest-path baseline for its chosen edge weights; RL has a stronger opportunity when conditions change and a learned policy can exploit useful state unavailable to that baseline.

### Simulation Model Limitations

This is a synthetic, aggregate, discrete-step simulation, not a packet-accurate emulator such as Mininet or a full network simulator such as ns-3. Link utilization, queue occupancy, packet drops, and latency are model estimates. In particular, queue state is simplified and the model does not fully schedule each queued packet's departure time. Treat measured results as comparative evidence within this model, not as claims about production networks. Validate a promising result with a more detailed simulator or an emulated testbed before making real-world performance claims.

---

## 📐 Project Structure

```
cn cbp/
├── backend/
│   ├── app/
│   │   ├── config.py                # Configuration and boundaries (1-1000 nodes)
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── api/                     # REST and WebSocket endpoints
│   │   │   ├── topology.py
│   │   │   ├── simulation.py
│   │   │   ├── optimization.py
│   │   │   ├── rl.py
│   │   │   └── experiments.py
│   │   └── core/                    # Simulation & AI Engine
│   │       ├── topology.py          # Scalable topology generator
│   │       ├── validator.py         # Network and reachability validator
│   │       ├── traffic.py           # Synthetic traffic model generator
│   │       ├── traditional_routing.py # Dijkstra & Least-Loaded routing
│   │       ├── simulator.py         # Dynamic discrete-event simulator
│   │       ├── metrics.py           # Ground-truth metrics calculation
│   │       ├── storage.py           # Experiment persistence
│   │       └── rl/                  # PyTorch PPO Agent & RoutingEnv
│   └── tests/                       # Unit and benchmark test suites
├── frontend/
│   ├── src/
│   │   ├── index.css                # Enterprise dark theme design system
│   │   ├── App.jsx                  # Main application container
│   │   ├── components/
│   │   │   ├── Navbar.jsx           # Navigation & status bar
│   │   │   ├── NetworkBuilder.jsx   # Configuration & 1-1000 node controls
│   │   │   ├── GraphViewer.jsx      # High-performance Canvas graph viewer
│   │   │   ├── SimulationWorkspace.jsx # Simulation playback & terminal log
│   │   │   ├── OptimizationWorkspace.jsx # Side-by-side PPO vs Dijkstra evaluation
│   │   │   ├── ExperimentHistory.jsx # Historical audit ledger
│   │   │   ├── NodeLinkDrawer.jsx   # Telemetry inspector drawer
│   │   │   └── MetricsCards.jsx     # Telemetry metric cards
│   │   └── services/api.js          # REST & WebSocket client
│   └── vite.config.js
├── run_all.sh                       # Launcher script
└── README.md
```

### Repeatable burst-congestion PPO demonstration

In Network Builder, choose **Burst Congestion**. This loads a deterministic five-node topology with a two-hop route containing a 100 Mbps bottleneck and a three-hop alternative made of 1 Gbps links. It selects bursty traffic and disables injected link failures so congestion is the changing condition under study. The configured burst load exceeds the bottleneck capacity, creating an opportunity for a policy that avoids congestion to improve delivery.

Open Optimization, select **Dijkstra (Static Shortest Path)** (selected by default for this preset), train PPO on this topology, then run the head-to-head evaluation. Training and evaluation are separate operations. The preset trains for 100 episodes. Select 1, 5, or 10 evaluation seeds; the page reports per-metric means and the number of runs where PPO performed better. Each replicate is saved separately in Experiment History. Compare packet loss, delivered throughput, latency, route, and routing computation time. The scenario is a test hypothesis, not a promised result: PPO may still fail to learn a better route. For stronger evidence, also run **Dijkstra (Delay-Sensitive)** as an adaptive baseline. Report every seed and result, not only the best run.
