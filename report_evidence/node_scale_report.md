# NETRA node-count scaling comparison

**Run configuration:** Random topology, high density, mixed traffic, dynamic conditions enabled, 10 simulation steps, source node 0, destination `min(50, node_count-1)`, matched seeds 42?46. Each method uses a fresh simulator and the same generated graph/seed per pair. Traditional method is `dijkstra_dynamic`; RL method is `ppo_residual` using the loaded repository candidate checkpoint. All metrics are simulator-model outputs, not real network measurements.

## Per-node-count results

Values are mean ? sample standard deviation over successful seeds. Latency/loss/utilization/decision time: lower is generally preferable; throughput: higher is preferable. `RL vs Dijkstra %` uses `(RL mean - Dijkstra mean) / Dijkstra mean ? 100`, so negative favors RL only for lower-is-better metrics.

| Nodes | Edges | Metric | Dijkstra dynamic | PPO residual | RL vs Dijkstra % | Seeds |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 1 | Mean latency (ms) | 14.1220 ? 7.6335 | 14.1220 ? 7.6335 | 0.0000 | 5/5 |
| 2 | 1 | Packet loss (%) | 9.7160 ? 16.1750 | 9.7160 ? 16.1750 | 0.0000 | 5/5 |
| 2 | 1 | Throughput (Mbps) | 90.6340 ? 25.9879 | 90.6340 ? 25.9879 | 0.0000 | 5/5 |
| 2 | 1 | Mean link utilization (%) | 31.9540 ? 21.2516 | 31.9540 ? 21.2516 | 0.0000 | 5/5 |
| 2 | 1 | Routing decision time (ms) | 0.0717 ? 0.0163 | 2.5822 ? 3.8609 | 3503.4608 | 5/5 |
| 5 | 4 | Mean latency (ms) | 16.3720 ? 9.7936 | 16.3720 ? 9.7936 | 0.0000 | 5/5 |
| 5 | 4 | Packet loss (%) | 52.7560 ? 8.9556 | 52.7560 ? 8.9556 | 0.0000 | 5/5 |
| 5 | 4 | Throughput (Mbps) | 47.4726 ? 15.1658 | 47.4726 ? 15.1658 | 0.0000 | 5/5 |
| 5 | 4 | Mean link utilization (%) | 15.0500 ? 5.0292 | 15.0500 ? 5.0292 | 0.0000 | 5/5 |
| 5 | 4 | Routing decision time (ms) | 0.0627 ? 0.0172 | 0.5582 ? 0.0317 | 790.5552 | 5/5 |
| 10 | 21 | Mean latency (ms) | 12.4380 ? 3.7398 | 20.9280 ? 9.8138 | 68.2586 | 5/5 |
| 10 | 21 | Packet loss (%) | 16.3820 ? 15.9128 | 4.6880 ? 10.4827 | -71.3832 | 5/5 |
| 10 | 21 | Throughput (Mbps) | 82.0790 ? 13.4579 | 95.5432 ? 22.5511 | 16.4040 | 5/5 |
| 10 | 21 | Mean link utilization (%) | 13.4000 ? 2.0688 | 11.3740 ? 1.0137 | -15.1194 | 5/5 |
| 10 | 21 | Routing decision time (ms) | 0.1155 ? 0.0258 | 0.9653 ? 0.1123 | 735.4336 | 5/5 |
| 20 | 119 | Mean latency (ms) | 12.3080 ? 2.1695 | 15.5840 ? 4.4898 | 26.6168 | 5/5 |
| 20 | 119 | Packet loss (%) | 7.3980 ? 10.6428 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 20 | 119 | Throughput (Mbps) | 91.7802 ? 14.9336 | 100.2624 ? 20.0536 | 9.2419 | 5/5 |
| 20 | 119 | Mean link utilization (%) | 10.6180 ? 0.3832 | 10.3160 ? 0.4148 | -2.8442 | 5/5 |
| 20 | 119 | Routing decision time (ms) | 0.2594 ? 0.0328 | 1.3878 ? 0.2131 | 434.9368 | 5/5 |
| 50 | 406 | Mean latency (ms) | 14.0240 ? 4.2332 | 18.0740 ? 3.7517 | 28.8791 | 5/5 |
| 50 | 406 | Packet loss (%) | 11.5460 ? 8.7272 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 50 | 406 | Throughput (Mbps) | 87.6476 ? 13.4462 | 100.2624 ? 20.0536 | 14.3926 | 5/5 |
| 50 | 406 | Mean link utilization (%) | 10.7560 ? 0.2011 | 10.6340 ? 0.1324 | -1.1343 | 5/5 |
| 50 | 406 | Routing decision time (ms) | 0.6942 ? 0.0794 | 2.4036 ? 0.2826 | 246.2245 | 5/5 |
| 100 | 905 | Mean latency (ms) | 12.0200 ? 3.0015 | 19.9800 ? 7.2858 | 66.2230 | 5/5 |
| 100 | 905 | Packet loss (%) | 11.8880 ? 14.8385 | 3.8240 ? 8.5507 | -67.8331 | 5/5 |
| 100 | 905 | Throughput (Mbps) | 87.8996 ? 23.1454 | 96.6140 ? 22.6527 | 9.9140 | 5/5 |
| 100 | 905 | Mean link utilization (%) | 10.6900 ? 0.0784 | 10.6460 ? 0.0555 | -0.4116 | 5/5 |
| 100 | 905 | Routing decision time (ms) | 1.3089 ? 0.1884 | 3.4928 ? 0.5341 | 166.8551 | 5/5 |
| 245 | 2352 | Mean latency (ms) | 11.8800 ? 3.4771 | 16.4420 ? 5.2906 | 38.4007 | 5/5 |
| 245 | 2352 | Packet loss (%) | 7.6240 ? 8.0674 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 245 | 2352 | Throughput (Mbps) | 92.4696 ? 20.7271 | 100.2624 ? 20.0536 | 8.4274 | 5/5 |
| 245 | 2352 | Mean link utilization (%) | 10.7120 ? 0.0502 | 10.6960 ? 0.0451 | -0.1494 | 5/5 |
| 245 | 2352 | Routing decision time (ms) | 5.4569 ? 1.8263 | 7.5562 ? 0.2248 | 38.4702 | 5/5 |
| 500 | 4890 | Mean latency (ms) | 12.2080 ? 1.3440 | 24.1800 ? 5.5720 | 98.0668 | 5/5 |
| 500 | 4890 | Packet loss (%) | 16.4380 ? 14.9219 | 1.3100 ? 2.9292 | -92.0307 | 5/5 |
| 500 | 4890 | Throughput (Mbps) | 82.0390 ? 12.5362 | 99.0126 ? 20.6199 | 20.6897 | 5/5 |
| 500 | 4890 | Mean link utilization (%) | 10.7280 ? 0.0766 | 10.7160 ? 0.0699 | -0.1119 | 5/5 |
| 500 | 4890 | Routing decision time (ms) | 10.0629 ? 2.0339 | 14.7302 ? 1.4333 | 46.3814 | 5/5 |
| 685 | 6746 | Mean latency (ms) | 11.6580 ? 3.0652 | 23.3340 ? 10.2258 | 100.1544 | 5/5 |
| 685 | 6746 | Packet loss (%) | 15.1500 ? 15.9729 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 685 | 6746 | Throughput (Mbps) | 83.1724 ? 12.5312 | 100.2624 ? 20.0536 | 20.5477 | 5/5 |
| 685 | 6746 | Mean link utilization (%) | 10.7260 ? 0.0498 | 10.7160 ? 0.0472 | -0.0932 | 5/5 |
| 685 | 6746 | Routing decision time (ms) | 13.7722 ? 2.3770 | 16.6259 ? 3.6443 | 20.7202 | 5/5 |
| 1000 | 9899 | Mean latency (ms) | 13.2860 ? 3.2522 | 21.1420 ? 4.0307 | 59.1299 | 5/5 |
| 1000 | 9899 | Packet loss (%) | 19.5320 ? 12.5493 | 0.1020 ? 0.2281 | -99.4778 | 5/5 |
| 1000 | 9899 | Throughput (Mbps) | 78.7170 ? 5.2513 | 100.1530 ? 20.0054 | 27.2317 | 5/5 |
| 1000 | 9899 | Mean link utilization (%) | 10.7360 ? 0.0428 | 10.7260 ? 0.0385 | -0.0931 | 5/5 |
| 1000 | 9899 | Routing decision time (ms) | 16.2000 ? 2.3196 | 20.3558 ? 2.9301 | 25.6533 | 5/5 |

## Run status

- Successful method-runs: 100 of 100.
- Failed paired cases: 0.
- A one-node case is omitted: a source/destination routing pair requires distinct nodes. The 2-node case is included.
- Training time is not included; this experiment evaluates the existing checkpoint. The repeated decision time is the simulator-reported `routing_computation_time_ms`; wall time is separately preserved in the raw CSV.
- Outputs are deterministic-seed test cases but the simulator is synthetic and simplified. Do not describe results as real-network measurements.

## Failures

None.

## Evidence files

- `node_scale_raw.csv`: one row per method and seed, including paths, metrics, timing and dynamic-event counts.
- `node_scale_summary.csv`: means, sample SDs and relative differences.
- `node_scale_errors.json`: failures, if any.
- `node_scale_report.md`: this report.
