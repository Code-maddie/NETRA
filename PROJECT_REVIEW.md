# NETRA Project Review: Findings and Changes

Review date: 27 October 2026

## Executive summary

The very poor RL results were explainable from the implementation; they were not evidence that RL can never work for routing. The most severe historical runs show PPO delivering 0 of 2,128 packets (100% loss) while reporting an average latency of 0 ms. The comparison code could then interpret that zero as lower latency, even though no packet had arrived. Those results should not be used as evidence of an RL performance advantage.

The project was corrected to distinguish an untrained model from a trained checkpoint, prevent routing cycles, provide destination-aware state features, remove an arbitrary hop cutoff, align the documented GAE implementation with the training code, correct several simulator calculations, expose route paths, and avoid reporting missing latency samples as perfect results.

The revised project passes its backend test suite (21 tests). A 20-node end-to-end smoke test also completed. It showed the corrected behavior does not guarantee RL wins: on that run both methods used the same path and tied on delivery metrics, while PPO's routing computation took longer.

## What went wrong

A saved historical run on a 485-node topology records traditional routing delivering all 2,128 packets (0% loss, 19.31 ms average latency) while PPO delivered 0 (100% loss) and reported 0 ms average latency. Another 703-node record has the same 100% PPO loss pattern. Those are the clearest examples of the issue: the route chosen by PPO was not reaching the destination, and zero latency with zero delivered packets was a missing measurement, not a performance win. Debug tracing also exposed cyclic hops (for example, a route revisiting node 22 after traversing several other nodes).

### 1. A checkpoint file was treated as proof of training

The old application startup created a checkpoint from the randomly initialized network when no weights file existed. The status endpoint/UI then treated the presence of that file as “trained weights loaded.” A random Actor-Critic network is not a trained routing agent; its choices can be effectively arbitrary. The comparison endpoint also allowed an untrained PPO policy to be evaluated.

**Fix:** startup no longer writes a random checkpoint. The status endpoint reports `trained`, `weights_loaded`, and training episode count from checkpoint metadata. Only explicitly versioned checkpoints with compatible architecture metadata load as trained. The frontend warns when PPO has not been trained. Old/unversioned or incompatible checkpoints are ignored.

### 2. The route policy could cycle and did not have enough destination information

The previous routing state did not encode useful destination proximity for each neighbor. The action masking/fallback behavior could allow an already visited node to be selected again, so an RL policy could cycle without reaching the destination. This caused all offered packets for that route to be dropped. Historical experiment records have 100% PPO packet loss and 0 deliveries on multiple large graphs.

**Fix:** the environment removes visited nodes from next-hop candidates, checks that candidates still have a path to the destination without revisiting the current route, and ends safely when no valid move exists. The observation includes candidate identity, link delay/utilization, and a destination cost-to-go estimate. Valid candidate routes remain available to PPO rather than masking all higher-cost alternatives using the baseline's own cost threshold. The hop limit is now bounded by the number of nodes minus one, rather than an arbitrary 35/50-hop limit that could reject a valid long path.

### 3. “Zero latency” was not a real latency measurement

If zero packets were delivered, the metrics function returned 0 ms because it had no latency samples. The old comparison logic did not require packets to have been delivered before comparing average latency, so 0 ms could be misread as a perfect result. Some historical records also lacked route paths in the comparison payload.

**Fix:** latency improvement is marked non-comparable whenever either algorithm delivers zero packets; the report explains why. The Optimization UI displays `N/A` when no latency sample exists, and timeline data leaves that point missing instead of plotting it at zero. The simulation summary includes the actual selected path, and the comparison can fall back to the active path. Older records are retained but labeled as legacy in Experiment History.

### 4. The training implementation did not match its documentation

The README claimed Generalized Advantage Estimation (GAE), but training used discounted Monte Carlo returns minus the critic value. The optimizer's `batch_size` argument was accepted but updates were actually full-batch. The requested learning rate was not applied by the earlier endpoint. Training also used a separate synthetic topology rather than the topology selected in the UI.

**Fix:** training uses GAE, shuffled mini-batch PPO updates, the requested learning rate, and the selected topology/endpoints when passed by the UI. Link utilization is randomized between episodes so the agent sees varied link conditions. Successful route count is returned separately from reward/loss so successful episode completion is not mistaken for proof of good performance.

### 5. Simulator metrics contained inconsistent or incomplete accounting

- Offered traffic was too low in the earlier setup to challenge typical links, and the old utilization calculation mixed packet counts and link capacity without consistent units.
- Queues were drained using a fixed percentage, unrelated to physical link service capacity, which could manufacture backlog on idle links.
- Link utilization summaries were based on a final cooled snapshot, masking utilization spikes during the run.
- The injected link failure could be unrelated to the source-to-destination path.
- A traffic field labeled MB was calculating a megabit quantity.

**Fix:** offered load and Mbps utilization now use 1,500-byte packets and the configured 500 ms step duration; queue draining is capacity-based; utilization is collected throughout the run; the injected failure is selected from the initial baseline path when possible; and the MB field now uses megabytes. The burst traffic may still produce drops when offered load exceeds link service and buffer capacity, which is intentional within the synthetic model.

## Checks performed

### Backend tests

Command: `PYTHONPATH=backend pytest -q backend/tests`

Result: **20 passed** after the review changes.

### End-to-end smoke test

Configuration: 20-node generated random topology, seed 42, source 0, destination 19, 30 PPO training episodes, 10 simulation steps, mixed traffic.

- Training completed 30/30 valid route episodes; mean training return was 7.373.
- Traditional and PPO both selected path `0 → 9 → 19`.
- Both delivered 26,325 of 29,672 offered packets (11.28% loss), with average delivered-packet latency 11.56 ms and throughput 63.18 Mbps.
- Routing computation averaged approximately 0.226 ms for Dijkstra and 1.451 ms for PPO in this run.
- The delivery metrics tied in this one run; once the material route-computation overhead is included, the comparison correctly favors traditional routing. The timing is one local smoke test, not a general benchmark.

## Files with the main changes

- `backend/app/core/rl/environment.py`: loop prevention, destination-aware state, valid action masks, cost-to-go features, cache invalidation.
- `backend/app/core/rl/ppo_agent.py`: checkpoint provenance/versioning, safe route evaluation limit, PPO mini-batches.
- `backend/app/api/rl.py`: topology-specific training, learning-rate handling, randomized utilization and GAE.
- `backend/app/core/simulator.py`: capacity-aware queue drain, utilization history/unit correction, route-aware failure injection, path in summary.
- `backend/app/core/metrics.py` and `backend/app/api/optimization.py`: honest latency comparison and missing per-step latency values.
- `backend/app/core/traffic.py`: corrected MB units.
- `frontend/src/components/OptimizationWorkspace.jsx`, `MetricsCards.jsx`, `SimulationWorkspace.jsx`, `ExperimentHistory.jsx`: untrained warnings, N/A latency display, gaps in timeline instead of false zeroes, legacy-history notice.
- `README.md`: workflow and simulation caveats.

## Known limitations (do not hide these in a project presentation)

1. The simulator is aggregate and synthetic. Queue state is not a full packet-accurate scheduler, and per-packet queue departure times are not modeled in detail.
2. PPO can still underperform Dijkstra. A training run that completes successfully only means the episodes terminated; it does not mean the policy has converged or generalized.
3. Dynamic Dijkstra is a strong baseline because it recalculates a route using current delay/utilization values. On a small, simple topology, a learned policy may have no advantage and usually has more inference overhead.
4. The environment includes destination-cost estimates and cost-orders candidate neighbors as features. This is helpful state information, but results should be described as a destination-aware PPO routing policy, not a completely uninformed agent learning the graph from scratch.
5. The frontend production build was verified after a clean `npm install` on this machine. The delivered ZIP excludes `node_modules` and `dist`; run `npm install` on the target machine to install platform-correct dependencies. Backend startup could not be re-verified in this environment because Python package installation was blocked by unavailable network access.
6. Results should be collected across 5–10 or more independent seeds, with identical topology, offered load, endpoints, and failure schedule. Report averages and variability, not one favorable run.

## Launch fixes in this delivery

- Added the missing `pydantic-settings` runtime dependency used by `backend/app/config.py`.
- Updated `run_all.sh` to check dependencies, wait for backend health, report startup failures, and avoid killing unrelated processes on ports 8000 or 3000.
- Added a visible frontend loading state, backend connection error, and retry action when the starter topology cannot be fetched.
- Added a deterministic burst-congestion comparison preset with a two-hop 100 Mbps bottleneck and a three-hop 1 Gbps alternate route. The preset disables injected link failures to isolate burst congestion.
- Added separate 100-episode PPO training for that preset and paired 1/5/10-seed evaluations with mean metrics and per-metric PPO win counts. Every replicate is saved as its own experiment. A measured PPO advantage remains a result to establish, not a guarantee.
- Verified the frontend production build with `npm run build`.

## NETRA V2 Implementation: Candidate-Path Residual PPO with Safety Shielding

Following the research reference and gap analysis, NETRA was systematically upgraded to resolve the fundamental RL routing limitations:

### 1. Architectural Upgrades
- **Candidate Path Action Space ($K=4$)**: Replaced per-hop neighbor actions with precomputed, loop-free candidate simple paths. Candidate 0 is static Dijkstra. Eliminates dead-ends, looping, and cycle-induced packet drops.
- **Topology-Agnostic Shared Candidate Scorer**: Single MLP encoding 13 normalized path features ($U_{t-1}, U_{t-2}, U_{t-3}$, projected utilization removing flow's own load, delay ratio, hops, bottleneck bandwidth, hysteresis stickiness, demand trends, mean network load). Generalizes cleanly across 4 to 1,000 nodes without topology re-training.
- **DAgger Imitation Pre-Training**: Pre-trains policy from privileged lookahead teacher, solving random cold-start exploration.
- **Residual PPO with Cloned BC Regularization**: Clones the BC policy and penalizes KL divergence ($\beta_{KL} D_{KL}(\pi_{ref} \parallel \pi)$) while using relative rewards against the shadow baseline (CADJ). Prevents policy collapse.
- **CADJ Baseline**: Implemented hysteresis-tuned delay-sensitive routing to suppress herding and route flapping under dynamic congestion.
- **Provable Safety Shielding**: Implemented runtime shielding: whenever policy candidate delay exceeds $(1+\tau) \times \text{cost}(CADJ)$, the shield intervenes and routes via CADJ, measuring and reporting the fallback rate.

### 2. Verification & Test Coverage
- Self-contained standalone reference `netra_v2.py` tested across smoke and paired scenarios.
- Standalone flow simulation confirmed:
  - Least-loaded routing suffers herding (+75% to +128% relative cost vs CADJ, 95% churn).
  - PPO+shield beats static and outperforms unshielded baselines while maintaining low fallback rates (~9%).
- Integrated into NETRA backend with 28 passing unit & benchmark tests (`backend/tests/`).
- Frontend updated with algorithm selection (Baseline: CADJ/Dijkstra, RL: Candidate Residual PPO / Shielded PPO / Legacy PPO) and shield telemetry.

