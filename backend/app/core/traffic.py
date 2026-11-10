"""
NETRA Synthetic Traffic Demand Generator
Implements Constant, Bursty, Periodic, and Mixed traffic patterns across discrete simulation steps.
"""
import math
import random
from typing import List, Dict, Any

def generate_traffic_schedule(
    pattern: str = "mixed",
    total_steps: int = 30,
    base_rate_packets: int = 50,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Generates a deterministic step-by-step traffic demand sequence.
    
    Parameters:
      pattern: 'constant', 'bursty', 'periodic', or 'mixed'.
      total_steps: Number of discrete steps in simulation.
      base_rate_packets: Average baseline packets per step.
      seed: Random seed for reproducibility.
      
    Returns:
      List of step demand dictionaries.
    """
    pattern = pattern.lower()
    rng = random.Random(seed)
    schedule: List[Dict[str, Any]] = []

    for step in range(total_steps):
        is_burst = False
        rate = base_rate_packets

        if pattern == "constant":
            # Stable rate with minor jitter (+/- 5%)
            jitter = rng.randint(-2, 2)
            rate = max(10, base_rate_packets + jitter)

        elif pattern == "bursty":
            # Low baseline with periodic sharp bursts (e.g. step % 6 == 0)
            if step % 7 == 3 or rng.random() < 0.22:
                is_burst = True
                burst_multiplier = rng.uniform(2.5, 4.0)
                rate = int(base_rate_packets * burst_multiplier)
            else:
                rate = int(base_rate_packets * rng.uniform(0.5, 0.9))

        elif pattern in ("random_bursts", "random-bursts"):
            if rng.random() < 0.35:
                is_burst = True
                rate = int(base_rate_packets * rng.uniform(2.0, 4.0))
            else:
                rate = int(base_rate_packets * rng.uniform(0.65, 1.05))

        elif pattern == "periodic":
            # Sinusoidal periodic demand wave
            phase = (2.0 * math.pi * step) / 10.0
            amplitude = base_rate_packets * 0.75
            rate = int(base_rate_packets + amplitude * math.sin(phase))
            rate = max(15, rate)

        else:  # "mixed" pattern
            # Base sinusoidal + random bursts
            phase = (2.0 * math.pi * step) / 12.0
            sin_val = math.sin(phase)
            harmonic_rate = base_rate_packets * (1.0 + 0.5 * sin_val)
            
            if step in [5, 12, 19, 26] or rng.random() < 0.18:
                is_burst = True
                rate = int(harmonic_rate * rng.uniform(2.2, 3.5))
            else:
                rate = int(harmonic_rate * rng.uniform(0.85, 1.15))

        schedule.append({
            "step": step,
            "pattern": pattern,
            "packets_offered": max(10, rate),
            "is_burst": is_burst,
            "data_volume_mb": round((rate * 1500) / 1_000_000, 3)  # Decimal MB, assuming 1,500-byte packets
        })

    return schedule
