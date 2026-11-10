"""
NETRA Configuration Module
Central application settings defining network bounds, topologies, simulation parameters,
and filesystem storage paths.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "NETRA"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Network Constraints (PRD section 5.1 & 10)
    MIN_NODES: int = 1
    MAX_NODES: int = 1000
    
    # Reference Configuration benchmark (PRD section 8)
    BENCHMARK_NODES: int = 685
    BENCHMARK_TOPOLOGY: str = "random"
    BENCHMARK_DENSITY: str = "high"
    BENCHMARK_SOURCE: int = 1
    BENCHMARK_DESTINATION: int = 50
    BENCHMARK_TRAFFIC: str = "mixed"
    
    # Supported Topologies
    SUPPORTED_TOPOLOGIES: List[str] = ["random", "scale_free", "mesh", "star", "ring", "line", "grid"]
    SUPPORTED_DENSITIES: List[str] = ["low", "medium", "high"]
    SUPPORTED_TRAFFIC_PATTERNS: List[str] = ["constant", "bursty", "random_bursts", "periodic", "mixed"]
    
    # Link Characteristic Defaults
    DEFAULT_LINK_CAPACITY_MBPS: float = 1000.0  # 1 Gbps
    DEFAULT_LINK_BASE_DELAY_MS: float = 5.0    # 5 ms base propagation delay
    CONGESTION_UTILIZATION_THRESHOLD: float = 0.80  # 80% utilization considered congested
    BUFFER_SIZE_PACKETS: int = 250              # Max packets in queue before drop
    
    # Dynamic Simulation Parameters
    DEFAULT_SIMULATION_STEPS: int = 30
    DEFAULT_STEP_DURATION_MS: int = 500
    
    # Storage and Artifact Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    EXPERIMENTS_FILE: Path = DATA_DIR / "experiments.json"
    MODEL_WEIGHTS_DIR: Path = BASE_DIR / "app" / "core" / "rl" / "weights"

    model_config = {"case_sensitive": True}

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.MODEL_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
