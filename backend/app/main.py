"""
NETRA — Network Engineering, Traffic Routing & Intelligence Platform
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import topology, simulation, routing, optimization, rl, experiments

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Interactive network simulation and routing intelligence platform comparing traditional routing with PPO reinforcement learning."
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Sub-routers
app.include_router(topology.router, prefix=settings.API_PREFIX)
app.include_router(simulation.router, prefix=settings.API_PREFIX)
app.include_router(routing.router, prefix=settings.API_PREFIX)
app.include_router(optimization.router, prefix=settings.API_PREFIX)
app.include_router(rl.router, prefix=settings.API_PREFIX)
app.include_router(experiments.router, prefix=settings.API_PREFIX)

# No random checkpoint is written at startup. A policy is marked trained only
# after the explicit /api/rl/train workflow saves a versioned checkpoint.

@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "description": "Network Engineering, Traffic Routing & Intelligence Platform",
        "bounds": {
            "min_nodes": settings.MIN_NODES,
            "max_nodes": settings.MAX_NODES,
            "benchmark_nodes": settings.BENCHMARK_NODES
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "netra-backend"}
