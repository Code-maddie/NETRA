# NETRA additional topology and traffic cases

**Method:** 10-step paired runs; seeds 42?46; Dijkstra dynamic vs candidate PPO residual; same generated topology and seed per pair; existing trained checkpoint; source 0, destination min(50,n?1). All measurements are from the synthetic simulator.

Completed method-runs: 150 of 150. Failed scenarios: 0.

Values are mean ? sample standard deviation. Relative difference is `(RL - Dijkstra)/Dijkstra ? 100`; for latency/loss/utilization/decision time a negative value favors RL, while throughput is better when higher.

## 50-node random topology: density

| Scenario | Edges | Metric | Dijkstra dynamic | PPO residual | RL vs Dijkstra % | Seeds |
|---|---:|---|---:|---:|---:|---:|
| 50_random_low_mixed_dynamic | 96 | Latency (ms) | 28.6860 ? 9.5151 | 39.7840 ? 20.1078 | 38.6879 | 5/5 |
| 50_random_low_mixed_dynamic | 96 | Loss (%) | 17.9440 ? 12.6405 | 13.8400 ? 14.7747 | -22.8712 | 5/5 |
| 50_random_low_mixed_dynamic | 96 | Throughput (Mbps) | 80.8424 ? 11.7484 | 85.2332 ? 16.8239 | 5.4313 | 5/5 |
| 50_random_low_mixed_dynamic | 96 | Mean utilization (%) | 10.9900 ? 0.4118 | 10.6440 ? 0.4025 | -3.1483 | 5/5 |
| 50_random_low_mixed_dynamic | 96 | Decision time (ms) | 0.3521 ? 0.0612 | 1.7366 ? 0.2369 | 393.1675 | 5/5 |
| 50_random_medium_mixed_dynamic | 184 | Latency (ms) | 18.1660 ? 4.0918 | 25.6100 ? 4.0993 | 40.9777 | 5/5 |
| 50_random_medium_mixed_dynamic | 184 | Loss (%) | 24.8400 ? 10.3891 | 10.6180 ? 15.4582 | -57.2544 | 5/5 |
| 50_random_medium_mixed_dynamic | 184 | Throughput (Mbps) | 73.9584 ? 9.0081 | 88.0200 ? 15.5094 | 19.0129 | 5/5 |
| 50_random_medium_mixed_dynamic | 184 | Mean utilization (%) | 10.8380 ? 0.2341 | 10.6240 ? 0.4496 | -1.9745 | 5/5 |
| 50_random_medium_mixed_dynamic | 184 | Decision time (ms) | 0.4477 ? 0.1412 | 1.7102 ? 0.3023 | 282.0139 | 5/5 |
| 50_random_high_mixed_dynamic | 406 | Latency (ms) | 14.0240 ? 4.2332 | 18.0740 ? 3.7517 | 28.8791 | 5/5 |
| 50_random_high_mixed_dynamic | 406 | Loss (%) | 11.5460 ? 8.7272 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 50_random_high_mixed_dynamic | 406 | Throughput (Mbps) | 87.6476 ? 13.4462 | 100.2624 ? 20.0536 | 14.3926 | 5/5 |
| 50_random_high_mixed_dynamic | 406 | Mean utilization (%) | 10.7560 ? 0.2011 | 10.6340 ? 0.1324 | -1.1343 | 5/5 |
| 50_random_high_mixed_dynamic | 406 | Decision time (ms) | 0.7588 ? 0.0925 | 2.4236 ? 0.4563 | 219.4048 | 5/5 |

## 50-node topology shapes

| Scenario | Edges | Metric | Dijkstra dynamic | PPO residual | RL vs Dijkstra % | Seeds |
|---|---:|---|---:|---:|---:|---:|
| 50_scale_free_high_mixed_dynamic | 406 | Latency (ms) | 14.0240 ? 4.2332 | 18.0740 ? 3.7517 | 28.8791 | 5/5 |
| 50_scale_free_high_mixed_dynamic | 406 | Loss (%) | 11.5460 ? 8.7272 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 50_scale_free_high_mixed_dynamic | 406 | Throughput (Mbps) | 87.6476 ? 13.4462 | 100.2624 ? 20.0536 | 14.3926 | 5/5 |
| 50_scale_free_high_mixed_dynamic | 406 | Mean utilization (%) | 10.7560 ? 0.2011 | 10.6340 ? 0.1324 | -1.1343 | 5/5 |
| 50_scale_free_high_mixed_dynamic | 406 | Decision time (ms) | 0.7674 ? 0.1662 | 2.3727 ? 0.3009 | 209.1655 | 5/5 |
| 50_mesh_high_mixed_dynamic | 464 | Latency (ms) | 12.0020 ? 3.2909 | 19.8480 ? 1.9384 | 65.3724 | 5/5 |
| 50_mesh_high_mixed_dynamic | 464 | Loss (%) | 12.7960 ? 11.8572 | 3.8240 ? 8.5507 | -70.1157 | 5/5 |
| 50_mesh_high_mixed_dynamic | 464 | Throughput (Mbps) | 86.2230 ? 14.1887 | 96.6140 ? 22.6527 | 12.0513 | 5/5 |
| 50_mesh_high_mixed_dynamic | 464 | Mean utilization (%) | 10.7100 ? 0.1617 | 10.6380 ? 0.1556 | -0.6723 | 5/5 |
| 50_mesh_high_mixed_dynamic | 464 | Decision time (ms) | 0.7105 ? 0.0473 | 1.7372 ? 0.1051 | 144.5176 | 5/5 |
| 50_star_high_mixed_dynamic | 49 | Latency (ms) | 10.5620 ? 4.9923 | 10.5620 ? 4.9923 | 0.0000 | 5/5 |
| 50_star_high_mixed_dynamic | 49 | Loss (%) | 48.0020 ? 11.2565 | 48.0020 ? 11.2565 | 0.0000 | 5/5 |
| 50_star_high_mixed_dynamic | 49 | Throughput (Mbps) | 52.0570 ? 15.8209 | 52.0570 ? 15.8209 | 0.0000 | 5/5 |
| 50_star_high_mixed_dynamic | 49 | Mean utilization (%) | 10.4860 ? 0.6420 | 10.4860 ? 0.6420 | 0.0000 | 5/5 |
| 50_star_high_mixed_dynamic | 49 | Decision time (ms) | 0.1641 ? 0.0043 | 0.6930 ? 0.1229 | 322.3278 | 5/5 |
| 50_ring_high_mixed_dynamic | 50 | Latency (ms) | 254.0640 ? 32.8059 | 254.0640 ? 32.8059 | 0.0000 | 5/5 |
| 50_ring_high_mixed_dynamic | 50 | Loss (%) | 25.4040 ? 10.7028 | 25.4040 ? 10.7028 | 0.0000 | 5/5 |
| 50_ring_high_mixed_dynamic | 50 | Throughput (Mbps) | 73.3584 ? 8.9271 | 73.3584 ? 8.9271 | 0.0000 | 5/5 |
| 50_ring_high_mixed_dynamic | 50 | Mean utilization (%) | 25.3220 ? 2.9126 | 25.3220 ? 2.9126 | 0.0000 | 5/5 |
| 50_ring_high_mixed_dynamic | 50 | Decision time (ms) | 0.1912 ? 0.0538 | 1.5748 ? 0.2011 | 723.5331 | 5/5 |
| 50_line_high_mixed_dynamic | 49 | Latency (ms) | 621.2400 ? 16.0652 | 621.2400 ? 16.0652 | 0.0000 | 5/5 |
| 50_line_high_mixed_dynamic | 49 | Loss (%) | 55.8700 ? 6.5876 | 55.8700 ? 6.5876 | 0.0000 | 5/5 |
| 50_line_high_mixed_dynamic | 49 | Throughput (Mbps) | 43.5346 ? 7.0809 | 43.5346 ? 7.0809 | 0.0000 | 5/5 |
| 50_line_high_mixed_dynamic | 49 | Mean utilization (%) | 24.4680 ? 5.0444 | 24.4680 ? 5.0444 | 0.0000 | 5/5 |
| 50_line_high_mixed_dynamic | 49 | Decision time (ms) | 0.2419 ? 0.0569 | 1.1911 ? 0.1605 | 392.4915 | 5/5 |
| 50_grid_high_mixed_dynamic | 85 | Latency (ms) | 79.0240 ? 4.1804 | 92.1960 ? 9.0626 | 16.6684 | 5/5 |
| 50_grid_high_mixed_dynamic | 85 | Loss (%) | 26.0780 ? 10.1495 | 25.4040 ? 10.7028 | -2.5846 | 5/5 |
| 50_grid_high_mixed_dynamic | 85 | Throughput (Mbps) | 72.7040 ? 8.3526 | 73.3584 ? 8.9271 | 0.9001 | 5/5 |
| 50_grid_high_mixed_dynamic | 85 | Mean utilization (%) | 12.3260 ? 0.3514 | 11.6480 ? 0.5957 | -5.5006 | 5/5 |
| 50_grid_high_mixed_dynamic | 85 | Decision time (ms) | 0.3061 ? 0.0641 | 2.0994 ? 0.2437 | 585.9570 | 5/5 |

## 245-node traffic and dynamic-condition cases

| Scenario | Edges | Metric | Dijkstra dynamic | PPO residual | RL vs Dijkstra % | Seeds |
|---|---:|---|---:|---:|---:|---:|
| 245_random_high_constant_dynamic_false | 2352 | Latency (ms) | 10.4040 ? 4.8827 | 12.6940 ? 8.3929 | 22.0108 | 5/5 |
| 245_random_high_constant_dynamic_false | 2352 | Loss (%) | 0.0000 ? 0.0000 | 0.0000 ? 0.0000 | N/A | 5/5 |
| 245_random_high_constant_dynamic_false | 2352 | Throughput (Mbps) | 59.9982 ? 0.0111 | 59.9982 ? 0.0111 | 0.0000 | 5/5 |
| 245_random_high_constant_dynamic_false | 2352 | Mean utilization (%) | 10.6920 ? 0.0432 | 10.6900 ? 0.0458 | -0.0187 | 5/5 |
| 245_random_high_constant_dynamic_false | 2352 | Decision time (ms) | 4.3076 ? 1.1587 | 6.3083 ? 0.5845 | 46.4476 | 5/5 |
| 245_random_high_mixed_dynamic_false | 2352 | Latency (ms) | 10.9020 ? 4.8150 | 13.6780 ? 8.5715 | 25.4632 | 5/5 |
| 245_random_high_mixed_dynamic_false | 2352 | Loss (%) | 7.2980 ? 11.9570 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 245_random_high_mixed_dynamic_false | 2352 | Throughput (Mbps) | 92.5368 ? 21.3880 | 100.2624 ? 20.0536 | 8.3487 | 5/5 |
| 245_random_high_mixed_dynamic_false | 2352 | Mean utilization (%) | 10.7060 ? 0.0568 | 10.6940 ? 0.0451 | -0.1121 | 5/5 |
| 245_random_high_mixed_dynamic_false | 2352 | Decision time (ms) | 4.3017 ? 1.6436 | 6.7170 ? 0.9177 | 56.1481 | 5/5 |
| 245_random_high_mixed_dynamic_true | 2352 | Latency (ms) | 11.8800 ? 3.4771 | 16.4420 ? 5.2906 | 38.4007 | 5/5 |
| 245_random_high_mixed_dynamic_true | 2352 | Loss (%) | 7.6240 ? 8.0674 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 245_random_high_mixed_dynamic_true | 2352 | Throughput (Mbps) | 92.4696 ? 20.7271 | 100.2624 ? 20.0536 | 8.4274 | 5/5 |
| 245_random_high_mixed_dynamic_true | 2352 | Mean utilization (%) | 10.7120 ? 0.0502 | 10.6960 ? 0.0451 | -0.1494 | 5/5 |
| 245_random_high_mixed_dynamic_true | 2352 | Decision time (ms) | 4.0812 ? 0.6029 | 8.2992 ? 1.2283 | 103.3549 | 5/5 |
| 245_random_high_bursty_dynamic_true | 2352 | Latency (ms) | 11.3940 ? 4.1286 | 15.5780 ? 5.8286 | 36.7211 | 5/5 |
| 245_random_high_bursty_dynamic_true | 2352 | Loss (%) | 11.7980 ? 7.6536 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 245_random_high_bursty_dynamic_true | 2352 | Throughput (Mbps) | 83.6980 ? 18.2310 | 94.8878 ? 18.1587 | 13.3693 | 5/5 |
| 245_random_high_bursty_dynamic_true | 2352 | Mean utilization (%) | 10.7060 ? 0.0456 | 10.6940 ? 0.0467 | -0.1121 | 5/5 |
| 245_random_high_bursty_dynamic_true | 2352 | Decision time (ms) | 4.7162 ? 1.7428 | 7.1211 ? 0.6158 | 50.9917 | 5/5 |
| 245_random_high_random_bursts_dynamic_true | 2352 | Latency (ms) | 11.6160 ? 3.9239 | 16.3080 ? 6.5467 | 40.3926 | 5/5 |
| 245_random_high_random_bursts_dynamic_true | 2352 | Loss (%) | 6.3480 ? 5.2999 | 0.0000 ? 0.0000 | -100.0000 | 5/5 |
| 245_random_high_random_bursts_dynamic_true | 2352 | Throughput (Mbps) | 99.8378 ? 19.8129 | 107.1654 ? 24.0888 | 7.3395 | 5/5 |
| 245_random_high_random_bursts_dynamic_true | 2352 | Mean utilization (%) | 10.7100 ? 0.0510 | 10.6980 ? 0.0455 | -0.1120 | 5/5 |
| 245_random_high_random_bursts_dynamic_true | 2352 | Decision time (ms) | 3.9687 ? 0.5825 | 7.8039 ? 1.7950 | 96.6337 | 5/5 |
| 245_random_high_periodic_dynamic_true | 2352 | Latency (ms) | 11.8660 ? 3.5947 | 16.3320 ? 5.8317 | 37.6369 | 5/5 |
| 245_random_high_periodic_dynamic_true | 2352 | Loss (%) | 0.0000 ? 0.0000 | 0.0000 ? 0.0000 | N/A | 5/5 |
| 245_random_high_periodic_dynamic_true | 2352 | Throughput (Mbps) | 59.9900 ? 0.0000 | 59.9900 ? 0.0000 | 0.0000 | 5/5 |
| 245_random_high_periodic_dynamic_true | 2352 | Mean utilization (%) | 10.7000 ? 0.0442 | 10.6900 ? 0.0490 | -0.0935 | 5/5 |
| 245_random_high_periodic_dynamic_true | 2352 | Decision time (ms) | 3.8618 ? 0.5354 | 7.6441 ? 1.9234 | 97.9434 | 5/5 |

## Failures

None.

## Evidence files

- `case_matrix_raw.csv`: per-method/per-seed metrics, route, timing and dynamic event counts.
- `case_matrix_summary.csv`: means, sample SDs and relative differences.
- `case_matrix_errors.json`: failures, if any.
- `case_matrix_report.md`: this report.
