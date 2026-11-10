# NETRA — Product Requirements Document (PRD)

**Project title:** NETRA — Network Engineering, Traffic Routing & Intelligence Platform  
**Project type:** Computer Networks + Reinforcement Learning + Network Optimization  
**Project scope:** College project / academic prototype  
**Primary objective:** Develop an interactive network simulation platform that compares traditional routing algorithms with reinforcement learning-based routing under changing network conditions.

---

## 1. Product Overview

NETRA is a web-based network simulation and optimization platform that allows users to create networks of different sizes, simulate network traffic, observe congestion and link failures, and evaluate whether reinforcement learning (RL) can improve routing performance.

The system must use the existing project code and preserve the current Proximal Policy Optimization (PPO) agent wherever possible. Improvements should extend the existing implementation rather than replace it without evidence that replacement is necessary.

NETRA must provide an interactive graph-based visualization, a simulation engine, a routing comparison module, and an analytics dashboard.

The platform must produce results from actual simulation logic, not hardcoded or fabricated metrics.

## 2. Problem Statement

Traditional routing algorithms can provide reliable routes, but their performance may be affected by congestion, changing traffic demands, link failures, and varying network conditions. Reinforcement learning offers a potential way to adapt routing decisions using feedback from the network environment.

However, it is not always clear when RL performs better than traditional routing, how much improvement it provides, or what trade-offs it introduces.

NETRA addresses this problem by providing a controlled simulation environment where traditional routing and PPO-based RL routing are evaluated under comparable conditions. It measures latency, throughput, packet loss, congestion, routing cost, and computational overhead to determine when each approach performs better.

## 3. Project Objectives

1. Allow users to create configurable networks containing 1–1,000 nodes.
2. Support multiple network topologies and configurable connection density where applicable.
3. Simulate network traffic under static and dynamic conditions.
4. Preserve and integrate the existing PPO-based RL agent.
5. Compare RL routing against traditional routing using equivalent conditions.
6. Visualize network topology, traffic movement, routes, congestion, and failures.
7. Calculate and display meaningful performance metrics.
8. Identify the conditions under which RL improves, matches, or underperforms traditional routing.
9. Validate configurations and simulation results.
10. Maintain a responsive, visually polished interface suitable for a college project demonstration.

## 4. Target Users

- Students demonstrating computer networks and reinforcement learning concepts.
- Faculty evaluating routing optimization methodologies.
- Developers experimenting with network topologies, traffic patterns, and routing strategies.

## 5. Functional Requirements

### 5.1 Network Configuration

The user must be able to configure the network before starting a simulation.

**Node count**

- Minimum: 1 node.
- Maximum: 1,000 nodes.
- Allow every integer value in the range.
- Provide a numeric input and/or slider.
- Validate values before generating the network.
- Keep the maximum configurable through a central application setting.

The 1,000-node limit is the defined scope of this college project. It is not a claim that larger networks are impossible in principle.

**Topology options**

Support the following where compatible with the existing architecture:

- Random topology.
- Mesh topology.
- Star topology.
- Ring topology.
- Line topology.

Additional topologies may be included if they can be implemented and tested reliably.

**Connection density**

For applicable topologies, let users choose low, medium, or high connection density. Explain how density affects the number of links in generated random networks. Fixed-structure topologies should follow their structural rules rather than misleadingly applying a random density setting.

**Source and destination**

- Let the user select valid source and destination nodes.
- Populate selections from the generated network.
- Require distinct endpoints when a route between two nodes is requested.
- Validate that a path exists before running the experiment.
- Clearly report disconnected networks rather than silently inventing a route.

A one-node network should be treated as a special case. The system may demonstrate topology generation and basic validation, but must not pretend that a two-endpoint routing experiment is possible.

**Additional configuration options**

- Traffic pattern.
- Dynamic network conditions: enabled or disabled.
- Simulation duration or number of steps.
- Random seed, where supported, for reproducible experiments.
- Routing methods to compare.

### 5.2 Network Generation and Validation

The backend must generate the requested number of nodes and the links required by the selected topology.

Each network must have a consistent internal representation containing node identifiers and relevant link properties.

Possible link properties include:

- Delay or latency.
- Capacity.
- Current utilization.
- Link status.
- Packet loss probability, if modelled.
- Routing cost.

The network validation module must check:

- Requested node count.
- Valid topology configuration.
- Valid source and destination.
- Link and node identifiers.
- Reachability of the selected endpoints.
- Whether the network can support the requested experiment.

Generation and validation must be separate operations so the user can inspect the network before starting the simulation.

### 5.3 Dynamic Network Simulation

The simulator must represent traffic moving through a generated network and must update network conditions over time.

Supported conditions should include, where implemented:

- Traffic demand changes.
- Congestion and changing link utilization.
- Link failures and recovery.
- Changes in effective link delay.
- Different traffic arrival patterns.
- Alternative source-destination traffic demands.

**Traffic patterns**

- Constant traffic.
- Bursty traffic.
- Periodic traffic.
- Mixed traffic combining more than one pattern.

**Dynamic conditions**

When enabled, the simulator should apply configured events such as traffic bursts, link failures, and recovery. When disabled, it should keep the configured network conditions stable, apart from normal changes caused by the chosen traffic model.

The simulation engine must record the events that actually occur. The frontend must visualize these recorded events rather than creating independent animations that imply events that never happened.

### 5.4 Traditional Routing

Include a reliable traditional routing baseline.

The initial baseline should use Dijkstra's shortest-path algorithm with a clearly defined link cost, such as configured delay or routing weight.

Additional methods, such as equal-cost multipath or least-loaded routing, may be added if their behavior is correctly implemented.

The baseline must be evaluated using the same traffic demands and comparable network conditions as the RL method.

### 5.5 Reinforcement Learning Integration

Integrate the existing PPO-based agent into the simulation.

Before making changes, inspect the current agent, training procedure, state representation, action space, reward function, and evaluation code.

**Do not replace the existing PPO agent merely to introduce a different algorithm.**

The RL environment should expose appropriate network state information, potentially including:

- Current node and destination.
- Neighbor availability.
- Link delays and costs.
- Link utilization or congestion.
- Link status.
- Relevant traffic information.

The action space must correspond to valid routing decisions, such as selecting an available next hop. Invalid actions must be handled explicitly.

The reward function should reflect the project's routing objectives, including relevant measures of latency, packet loss, congestion, throughput, and route cost. Reward components should be normalized or weighted deliberately so one metric does not dominate unintentionally.

The system must distinguish between:

- Training an agent.
- Evaluating a trained agent.
- Running a comparison experiment.

Training should not be silently mixed with evaluation. If the agent is not trained or cannot be loaded, the application must display a clear status instead of reporting fabricated RL performance.

### 5.6 Traditional Routing vs RL Comparison

This is one of the project's most important features.

The user must be able to compare traditional routing with PPO-based RL routing under equivalent conditions.

Both methods must use:

- The same generated topology.
- The same traffic demands.
- The same configured link characteristics.
- The same dynamic event schedule or equivalent reproducible conditions.
- The same measurement definitions.

Where randomness affects the results, use controlled seeds or repeated trials when feasible. Record differences in conditions that prevent a perfectly paired comparison.

The comparison must answer:

- Which method achieved lower latency?
- Which method delivered more traffic successfully?
- Which method experienced less packet loss?
- Which method handled congestion more effectively?
- Which method achieved higher throughput?
- How much computational overhead did each method introduce?
- Under what conditions did RL improve or underperform?

**Do not assume RL will always win.** If traditional routing performs better for a particular scenario, report that result honestly.

### 5.7 Graph-Based Network Visualization

The network must be presented as an interactive graph or roadmap, not merely as a list of nodes.

The visualization should include:

- Nodes represented as graph vertices.
- Links represented as edges.
- Distinct source and destination indicators.
- Route highlighting.
- Zoom and pan.
- Node selection and details.
- Link selection and details.
- Visual indicators for congestion and failed links.
- A legend explaining all visual encodings.
- A layout that remains usable for networks containing up to 1,000 nodes.

The frontend must render the actual topology generated by the backend.

Use a graph-rendering library appropriate for large interactive graphs, such as Sigma.js with Graphology, or a compatible alternative that fits the existing frontend.

**Scalability requirements**

- Do not require every node label to remain visible at once.
- Support zoom-dependent labels or selective labels.
- Avoid unnecessary re-rendering of the entire graph for every traffic event.
- Allow the user to inspect a selected node or route.
- Keep topology rendering separate from the underlying simulation calculations.

For large networks, prioritize usability and responsive interaction over displaying every detail simultaneously.

### 5.8 Live Traffic Visualization

During a simulation, the user should be able to observe how traffic is routed through the network.

Show, where supported:

- Active routes.
- Traffic moving along selected paths.
- Changing link utilization.
- Congested links.
- Link failures and recovery.
- Routing changes made by the selected method.

Use aggregated traffic indicators or selected-route animations when rendering individual packets would become too expensive.

The animation must be tied to actual simulation events. If the system uses an abstract simulator rather than real packet transmission, label it as **simulated traffic**.

Do not describe simulated traffic as real-world live packet traffic.

### 5.9 Performance Analytics Dashboard

Display metrics derived from simulation data.

**Required metrics**

| Metric | Purpose |
|---|---|
| Average latency | Average time taken by delivered traffic |
| 95th-percentile latency | Measures higher-latency experiences |
| Throughput | Successfully delivered traffic per unit time |
| Packet loss | Fraction or percentage of traffic not delivered |
| Delivery success rate | Percentage of traffic successfully delivered |
| Link utilization | Degree to which link capacity is used |
| Congestion | Frequency, duration, or severity of congestion |
| Route cost | Total cost under the selected routing objective |
| Routing computation time | Time required to calculate routing decisions |
| RL reward | Reward accumulated during the evaluated run, when applicable |

Define the units and calculation method for each metric.

If a metric cannot be measured by the current simulator, display it as unavailable rather than inventing a value.

**Visualizations**

- Traditional routing vs RL comparison charts.
- Latency and throughput over time.
- Packet loss comparison.
- Link utilization trends.
- RL reward over time, where meaningful.
- Routing decisions and network event timelines.

Simulation results and optimization results must be distinct views with different purposes. The simulation view should focus on network behavior; the optimization view should focus on routing decisions, algorithm comparisons, and measured improvements.

### 5.10 Experiment History and Reproducibility

Store or retain enough experiment information to inspect and compare previous runs, subject to the project's storage design.

Each experiment should record:

- Experiment identifier.
- Network configuration.
- Topology and random seed, when available.
- Traffic configuration.
- Routing methods.
- Simulation duration or step count.
- Dynamic events.
- Agent version or checkpoint identifier, when available.
- Metric summaries.
- Validation errors or warnings.
- Experiment status.

Users should be able to review completed experiments and compare their results.

Do not claim two experiments are directly comparable if their configurations or measurement methods differ materially.

## 6. Frontend Requirements

The frontend should provide a polished, modern network operations dashboard.

### 6.1 Main Dashboard

Display:

- Project name and navigation.
- Network configuration summary.
- Current simulation status.
- Key performance metrics.
- Recent experiment information.
- Quick access to simulation and optimization.

### 6.2 Network Builder

Include:

- Node count input from 1 to 1,000.
- Topology selector.
- Connection density selector where applicable.
- Source and destination selectors.
- Traffic pattern selector.
- Dynamic conditions toggle.
- Simulation settings.
- Generate, validate, and reset actions.

### 6.3 Simulation Workspace

Include:

- Interactive graph.
- Start, pause, resume, and stop controls, where supported.
- Simulation progress.
- Selected route information.
- Traffic and network event indicators.
- Metric updates.
- Error and validation messages.

Controls must reflect actual backend capabilities. For example, do not display a functional pause button if the simulation cannot be paused.

### 6.4 Optimization Workspace

Include:

- Traditional routing vs PPO comparison.
- Metric selection.
- Performance charts.
- Routing decision explanations.
- RL reward information, where applicable.
- Relative and absolute performance differences.
- Conditions under which each method performed better.

For relative improvement, define the calculation and handle zero or missing baseline values safely.

### 6.5 Node and Link Details

Selecting a node should show its identifier, neighbors, relevant traffic information, and other supported properties.

Selecting a link should show its configured characteristics, status, utilization, and observed traffic metrics where available.

### 6.6 User Experience

- Responsive layout.
- Consistent typography, spacing, and visual hierarchy.
- Clear loading, empty, success, and error states.
- Readable charts and legends.
- Accessible controls and meaningful labels.
- No fake metrics, fake event logs, or fabricated algorithm results.

## 7. Backend Architecture

Preserve the existing backend framework and project structure unless an audit demonstrates a strong reason to change them.

The backend should separate these responsibilities:

1. API and configuration validation.
2. Topology generation.
3. Network validation.
4. Traffic generation.
5. Simulation execution.
6. Traditional routing.
7. PPO agent integration.
8. Metric calculation.
9. Event recording and streaming.
10. Experiment management.

These may be separate modules or classes within the existing codebase. Avoid unnecessary architectural rewrites.

### Suggested API capabilities

The exact endpoints should be adapted to the existing application.

| Endpoint | Purpose |
|---|---|
| `POST /api/topology/generate` | Generate a network from user configuration |
| `POST /api/topology/validate` | Validate the generated topology |
| `POST /api/simulation/start` | Start a simulation |
| `POST /api/simulation/{id}/stop` | Stop a running simulation |
| `GET /api/simulation/{id}/metrics` | Retrieve current or final metrics |
| `GET /api/simulation/{id}/events` | Retrieve recorded simulation events |
| `POST /api/optimization/evaluate` | Evaluate and compare routing methods |
| `GET /api/experiments/{id}` | Retrieve experiment configuration and results |

WebSockets or another suitable streaming mechanism may be used for live metrics and events. Polling is acceptable if it meets the project's performance needs.

Do not implement duplicate endpoints if equivalent functionality already exists. Extend the existing API instead.

## 8. Initial Reference Configuration

Use the following configuration as an initial benchmark:

- Node count: 685.
- Topology: random.
- Connection density: high.
- Source: node 1.
- Destination: node 50.
- Traffic pattern: mixed.
- Dynamic conditions: enabled.

This is a test configuration, not a fixed network size.

The application must also support user-selected node counts from 1 to 1,000, subject to validation and available resources.

## 9. Technology and Implementation Constraints

Use the existing technology stack wherever practical.

Potential components include:

- **Frontend:** Existing React or other current frontend framework.
- **Visualization:** Sigma.js/Graphology or a compatible scalable graph library.
- **Backend:** Existing Python framework.
- **RL:** Existing PPO implementation and its current training/evaluation stack.
- **Simulation:** Existing simulator extended with dynamic topology and traffic support.
- **Streaming:** WebSockets or an equivalent mechanism if required.
- **Testing:** Existing test framework plus additional unit and integration tests.

Do not introduce new libraries without checking compatibility, maintenance requirements, and installation impact.

A software network simulator must be clearly distinguished from packet-level emulation or a physical network. Packet-level tools such as Mininet and iperf3 may be future extensions if they are appropriate for the environment, but they are not prerequisites for the initial version.

## 10. Performance and Scalability

The application must support the configured maximum of 1,000 nodes without crashing for valid, supported configurations.

Performance requirements:

- Enforce the 1–1,000 node limit in both frontend and backend.
- Avoid dense all-pairs calculations when they are unnecessary.
- Use efficient graph representations and routing calculations.
- Avoid rendering excessive labels, animations, or event updates.
- Allow the user to reduce simulation duration or event frequency when needed.
- Provide clear progress and failure feedback for long-running experiments.
- Keep the interface responsive during simulation execution.

The system should be tested at representative sizes, including small networks, medium networks, and the 685- and 1,000-node benchmarks.

Do not promise a fixed execution time until it has been measured on the target environment.

## 11. Validation and Testing

### Unit tests

Test:

- Node count boundaries: 1, 2, and 1,000.
- Rejection of 0, negative values, non-integer values, and values above 1,000.
- Topology generation.
- Source and destination validation.
- Connectivity and route existence.
- Traditional routing correctness.
- PPO action validity.
- Metric calculations.
- Dynamic event processing.

### Integration tests

Verify:

- Frontend configuration reaches the backend correctly.
- The generated network matches the requested node count.
- Simulation events match the actual simulator state.
- Both routing methods receive comparable conditions.
- The frontend displays backend-calculated metrics.
- Errors are surfaced to the user.
- Completed experiments retain their results.

### Performance tests

Test representative configurations such as 50, 245, 685, and 1,000 nodes.

Measure topology generation time, routing calculation time, simulation throughput, memory use, and graph responsiveness.

The 1,000-node benchmark should be considered supported only after the relevant workflows have been tested successfully.

### Result validation

- Check for missing or invalid metric values.
- Verify packet and traffic accounting.
- Ensure failed links are not used unless the routing method explicitly models a recovery mechanism.
- Ensure reported improvements match the underlying metric values.
- Record experiment configuration and relevant randomness.
- Never replace failed experiments with fabricated successful results.

## 12. Implementation Phases

### Phase 1 — Existing Project Audit

Inspect the frontend, backend, PPO agent, routing algorithms, API endpoints, simulation logic, and existing tests.

Identify duplicated logic, incomplete features, and the reason simulation and optimization currently appear to produce the same output.

Produce a file-by-file implementation plan before making major changes.

### Phase 2 — Configurable Network Builder

Implement the 1–1,000 node selector, supported topologies, density settings, source/destination selection, network generation, and validation.

### Phase 3 — Dynamic Simulation and Traffic

Implement or extend traffic patterns, link utilization, congestion, failure and recovery events, simulation controls, and event recording.

### Phase 4 — PPO Integration

Integrate the existing PPO agent with the simulation environment. Validate state and action handling, reward calculation, checkpoint loading, and evaluation behavior.

### Phase 5 — Routing Comparison

Run traditional and RL methods under equivalent conditions. Calculate metrics and show genuine performance differences without assuming a particular winner.

### Phase 6 — Scalable Visualization

Connect the frontend graph to backend-generated topology and simulation events. Implement route highlighting, selected node/link details, and scalable rendering for larger graphs.

### Phase 7 — Analytics and Experiment History

Implement comparison charts, time-series metrics, experiment records, and result inspection.

### Phase 8 — Final Validation

Run unit, integration, and performance tests. Fix failures, document supported functionality, and prepare a reliable demonstration configuration.

Do not mark a phase complete solely because the interface exists; verify its behavior through tests or a reproducible demonstration.

## 13. Acceptance Criteria

The project is ready for demonstration when:

1. A user can select any valid node count from 1 to 1,000.
2. Invalid node counts are rejected with a clear explanation.
3. Supported topologies are generated according to their defined rules.
4. Network validation reports disconnected or otherwise invalid configurations.
5. Valid routing experiments can be executed.
6. Traffic and dynamic events reflect the actual simulation state.
7. The existing PPO agent can be evaluated through the integrated workflow.
8. Traditional routing and PPO routing can be compared under equivalent conditions.
9. The dashboard reports calculated metrics with clear units and definitions.
10. The graph remains usable at the 1,000-node benchmark.
11. Simulation and optimization views have distinct, meaningful purposes.
12. The system explains errors and unsupported configurations rather than presenting misleading results.
13. Tests verify the key workflows, and performance limitations are documented.

## 14. Future Enhancements

These features are optional and should not delay completion of the core project:

- Packet-level network emulation.
- Importing real network topologies.
- Integration with real network telemetry.
- Graph neural network encoders.
- Additional routing algorithms.
- More advanced multi-flow traffic models.
- Exportable experiment reports.
- Larger network sizes beyond 1,000 nodes after benchmarking.

## 15. Final Product Definition

NETRA must deliver a working, interactive network simulation and routing analysis platform—not just a visually impressive dashboard.

The user should be able to configure a network, generate and validate its topology, run a traffic simulation, compare traditional routing with PPO-based reinforcement learning, observe network behavior, and determine from measured results which routing approach performs better under specific conditions.

**Core principle:** Every displayed route, event, metric, and claimed improvement must be grounded in the actual implementation and recorded experiment data.