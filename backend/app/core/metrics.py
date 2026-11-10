"""
NETRA Performance Analytics & Honest Comparison Engine
Calculates true simulation metrics (Average latency, 95th-percentile latency,
throughput, packet loss %, delivery success rate, link utilization, route cost,
and computation overhead) and derives objective comparative deductions.
"""
from typing import Dict, Any, List, Optional
import numpy as np

def calculate_percentile(values: List[float], percentile: float = 95.0) -> float:
    """Calculates percentile safely from empirical list."""
    if not values:
        return 0.0
    return float(np.percentile(values, percentile))

def compute_simulation_metrics(
    packet_records: List[Dict[str, Any]],
    link_utilizations: List[float],
    total_time_ms: float,
    routing_computation_time_ms: float = 0.0,
    rl_reward: Optional[float] = None,
    shield_fallback_count: Optional[int] = None,
    shield_fallback_rate_pct: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Computes rigorous end-to-end telemetry metrics from raw simulation logs.
    """
    total_offered = len(packet_records)
    if total_offered == 0:
        return {
            "packets_offered": 0,
            "packets_delivered": 0,
            "packets_dropped": 0,
            "delivery_success_rate_pct": 0.0,
            "packet_loss_pct": 0.0,
            "throughput_pps": 0.0,
            "throughput_mbps": 0.0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "avg_link_utilization_pct": 0.0,
            "max_link_utilization_pct": 0.0,
            "congestion_frequency_pct": 0.0,
            "routing_computation_time_ms": routing_computation_time_ms,
            "rl_reward": rl_reward,
            "shield_fallback_count": shield_fallback_count,
            "shield_fallback_rate_pct": shield_fallback_rate_pct
        }

    delivered_packets = [p for p in packet_records if p.get("delivered", False)]
    dropped_packets = [p for p in packet_records if not p.get("delivered", False)]

    delivered_count = len(delivered_packets)
    dropped_count = len(dropped_packets)
    delivery_success_rate = (delivered_count / total_offered) * 100.0
    packet_loss_rate = (dropped_count / total_offered) * 100.0

    # Latency calculations from successfully delivered packets
    latencies = [p["latency_ms"] for p in delivered_packets if "latency_ms" in p]
    avg_latency = float(np.mean(latencies)) if latencies else 0.0
    p95_latency = calculate_percentile(latencies, 95.0) if latencies else 0.0
    min_latency = float(min(latencies)) if latencies else 0.0
    max_latency = float(max(latencies)) if latencies else 0.0

    # Throughput (delivered packets per second / megabits per second)
    time_sec = max(0.001, total_time_ms / 1000.0)
    throughput_pps = delivered_count / time_sec
    # Assuming 1500-byte packets
    throughput_mbps = (delivered_count * 1500 * 8) / (time_sec * 1_000_000)

    # Utilization and Congestion Metrics
    valid_utils = [u for u in link_utilizations if u is not None]
    avg_util = (float(np.mean(valid_utils)) * 100.0) if valid_utils else 0.0
    max_util = (float(max(valid_utils)) * 100.0) if valid_utils else 0.0
    congested_count = sum(1 for u in valid_utils if u >= 0.80)
    congestion_freq = (congested_count / max(1, len(valid_utils))) * 100.0

    res = {
        "packets_offered": total_offered,
        "packets_delivered": delivered_count,
        "packets_dropped": dropped_count,
        "delivery_success_rate_pct": round(delivery_success_rate, 2),
        "packet_loss_pct": round(packet_loss_rate, 2),
        "throughput_pps": round(throughput_pps, 2),
        "throughput_mbps": round(throughput_mbps, 3),
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "min_latency_ms": round(min_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "avg_link_utilization_pct": round(avg_util, 2),
        "max_link_utilization_pct": round(max_util, 2),
        "congestion_frequency_pct": round(congestion_freq, 2),
        "routing_computation_time_ms": round(routing_computation_time_ms, 4),
        "rl_reward": round(rl_reward, 3) if rl_reward is not None else None
    }
    if shield_fallback_count is not None:
        res["shield_fallback_count"] = shield_fallback_count
    if shield_fallback_rate_pct is not None:
        res["shield_fallback_rate_pct"] = shield_fallback_rate_pct
    return res


def compare_routing_results(
    traditional_result: Dict[str, Any],
    rl_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare real outcomes without treating an undelivered packet as zero latency."""
    t_metrics = traditional_result.get("metrics", {})
    rl_metrics = rl_result.get("metrics", {})

    t_latency = float(t_metrics.get("avg_latency_ms", 0.0) or 0.0)
    rl_latency = float(rl_metrics.get("avg_latency_ms", 0.0) or 0.0)
    t_loss = float(t_metrics.get("packet_loss_pct", 0.0) or 0.0)
    rl_loss = float(rl_metrics.get("packet_loss_pct", 0.0) or 0.0)
    t_tput = float(t_metrics.get("throughput_mbps", 0.0) or 0.0)
    rl_tput = float(rl_metrics.get("throughput_mbps", 0.0) or 0.0)
    t_comp = float(t_metrics.get("routing_computation_time_ms", 0.0) or 0.0)
    rl_comp = float(rl_metrics.get("routing_computation_time_ms", 0.0) or 0.0)
    t_delivered = int(t_metrics.get("packets_delivered", 0) or 0)
    rl_delivered = int(rl_metrics.get("packets_delivered", 0) or 0)

    def safe_rel_diff(baseline: float, candidate: float, lower_is_better: bool = True) -> Optional[float]:
        if baseline == 0.0:
            return None
        if lower_is_better:
            return round(((baseline - candidate) / baseline) * 100.0, 2)
        return round(((candidate - baseline) / baseline) * 100.0, 2)

    # A zero latency value means no latency samples were measured when no packets
    # arrived. It is not a perfect latency result and must not earn RL a point.
    latency_comparable = t_delivered > 0 and rl_delivered > 0
    latency_improvement_pct = (
        safe_rel_diff(t_latency, rl_latency, lower_is_better=True)
        if latency_comparable else None
    )
    loss_reduction_pct = safe_rel_diff(t_loss, rl_loss, lower_is_better=True)
    throughput_improvement_pct = safe_rel_diff(t_tput, rl_tput, lower_is_better=False)
    overhead_diff_pct = safe_rel_diff(t_comp, rl_comp, lower_is_better=True)
    loss_change_pp = round(t_loss - rl_loss, 2)

    score_traditional = 0
    score_rl = 0
    reasons: List[str] = []

    if latency_comparable:
        if rl_latency < t_latency and abs(rl_latency - t_latency) > 0.5:
            score_rl += 1
            reasons.append(f"RL achieved {latency_improvement_pct}% lower average latency among delivered packets.")
        elif t_latency < rl_latency and abs(t_latency - rl_latency) > 0.5:
            score_traditional += 1
            reasons.append(f"RL had {abs(latency_improvement_pct or 0.0)}% higher average latency than traditional routing.")
    elif t_delivered == 0 or rl_delivered == 0:
        reasons.append(
            f"Latency comparison skipped: delivered packets were traditional={t_delivered}, RL={rl_delivered}; "
            "zero measured latency is not evidence of faster delivery."
        )

    if rl_loss < t_loss:
        score_rl += 2
        if loss_reduction_pct is not None:
            reasons.append(f"RL reduced packet loss by {loss_reduction_pct}% relative to traditional routing.")
        else:
            reasons.append(f"RL packet loss was lower by {loss_change_pp} percentage points.")
    elif t_loss < rl_loss:
        score_traditional += 2
        reasons.append(f"Traditional routing had lower packet loss ({t_loss}% vs {rl_loss}%).")

    if rl_tput > t_tput:
        score_rl += 1
        reasons.append(f"RL delivered more throughput ({rl_tput} Mbps vs {t_tput} Mbps).")
    elif t_tput > rl_tput:
        score_traditional += 1
        reasons.append(f"Traditional routing delivered more throughput ({t_tput} Mbps vs {rl_tput} Mbps).")

    # Include route-computation overhead in the winner score when the gap is
    # material. Tiny timing differences are noisy, but a repeatable >10% gap
    # (and >0.05 ms) should not be described as a complete tie.
    timing_gap = abs(rl_comp - t_comp)
    material_timing_gap = max(0.05, 0.10 * min(t_comp, rl_comp))
    if t_comp > 0 and rl_comp > t_comp and timing_gap >= material_timing_gap:
        score_traditional += 1
        reasons.append(
            f"RL routing computation took longer ({rl_comp} ms vs {t_comp} ms for the traditional method)."
        )
    elif rl_comp > 0 and t_comp > rl_comp and timing_gap >= material_timing_gap:
        score_rl += 1
        reasons.append(
            f"Traditional routing computation took longer ({t_comp} ms vs {rl_comp} ms for RL)."
        )

    if score_rl > score_traditional:
        winner = "PPO Reinforcement Learning"
        verdict = "RL scored better on the measured metrics in this simulated run. Repeat across multiple seeds before generalizing."
    elif score_traditional > score_rl:
        winner = "Traditional Routing (Dijkstra)"
        verdict = "Traditional routing scored better on the measured metrics in this simulated run. This does not prove it always wins."
    else:
        winner = "Tie / Comparable Performance"
        verdict = "Neither method scored better under the comparison rules for this run. Repeat across multiple seeds for a stronger conclusion."

    return {
        "winner": winner,
        "verdict": verdict,
        "reasons": reasons,
        "latency_comparable": latency_comparable,
        "improvements": {
            "latency_improvement_pct": latency_improvement_pct,
            "packet_loss_reduction_pct": loss_reduction_pct,
            "packet_loss_change_percentage_points": loss_change_pp,
            "throughput_improvement_pct": throughput_improvement_pct,
            "computational_overhead_difference_pct": overhead_diff_pct,
        },
        "side_by_side": {
            "traditional": {
                "algorithm": traditional_result.get("routing_method", traditional_result.get("algorithm", "Dijkstra")),
                "path": traditional_result.get("path", traditional_result.get("active_path", [])),
                "hops": max(0, len(traditional_result.get("path", traditional_result.get("active_path", []))) - 1),
                "metrics": t_metrics,
            },
            "rl": {
                "algorithm": "PPO (Proximal Policy Optimization)",
                "path": rl_result.get("path", rl_result.get("active_path", [])),
                "hops": max(0, len(rl_result.get("path", rl_result.get("active_path", []))) - 1),
                "reward": rl_metrics.get("rl_reward"),
                "metrics": rl_metrics,
            },
        },
    }
