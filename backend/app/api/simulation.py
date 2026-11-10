"""
NETRA Dynamic Simulation API Endpoints & WebSocket Streamer
Allows starting, single-stepping, auto-running, stopping, and streaming network simulations.
"""
import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from app.core.simulator import NetworkSimulator
from app.core.validator import NetworkValidator

router = APIRouter(prefix="/simulation", tags=["Simulation"])

# Active in-memory simulation registry
active_simulations: Dict[str, NetworkSimulator] = {}

class StartSimulationRequest(BaseModel):
    topology_data: Dict[str, Any]
    source: int
    destination: int
    routing_method: str = Field(default="dijkstra_dynamic", description="dijkstra_static, dijkstra_dynamic, least_loaded, ppo")
    traffic_pattern: str = Field(default="mixed", description="constant, bursty, periodic, mixed")
    dynamic_conditions: bool = True
    total_steps: int = Field(default=30, ge=5, le=100)
    seed: Optional[int] = 42

@router.post("/start")
def api_start_simulation(req: StartSimulationRequest):
    """Initializes a new network simulation session."""
    # Validate endpoints before launching
    val = NetworkValidator.validate_network_and_endpoints(
        topology_data=req.topology_data,
        source=req.source,
        destination=req.destination
    )
    if not val["valid"]:
        raise HTTPException(status_code=400, detail={"errors": val["errors"]})

    sim = NetworkSimulator(
        topology_data=req.topology_data,
        source=req.source,
        destination=req.destination,
        routing_method=req.routing_method,
        traffic_pattern=req.traffic_pattern,
        dynamic_conditions=req.dynamic_conditions,
        total_steps=req.total_steps,
        seed=req.seed or 42
    )

    active_simulations[sim.simulation_id] = sim

    return {
        "success": True,
        "simulation_id": sim.simulation_id,
        "total_steps": sim.total_steps,
        "traffic_schedule": sim.traffic_schedule,
        "initial_event": sim.events[0]
    }

@router.post("/{sim_id}/step")
def api_step_simulation(sim_id: str):
    """Executes a single discrete step in the simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail=f"Simulation session {sim_id} not found.")
    sim = active_simulations[sim_id]
    result = sim.step()
    return result

@router.post("/{sim_id}/run")
def api_run_simulation(sim_id: str):
    """Runs all remaining steps of the simulation to completion."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail=f"Simulation session {sim_id} not found.")
    sim = active_simulations[sim_id]
    summary = sim.run_all()
    return summary

@router.post("/{sim_id}/stop")
def api_stop_simulation(sim_id: str):
    """Halts an active simulation."""
    if sim_id in active_simulations:
        active_simulations[sim_id].is_completed = True
        summary = active_simulations[sim_id].get_summary()
        return {"success": True, "summary": summary}
    return {"success": False, "message": "Simulation not found"}

@router.get("/{sim_id}/metrics")
def api_get_metrics(sim_id: str):
    """Returns current or final simulation metrics."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail=f"Simulation session {sim_id} not found.")
    sim = active_simulations[sim_id]
    return sim.get_summary()

@router.get("/{sim_id}/events")
def api_get_events(sim_id: str):
    """Returns recorded verifiable simulation events."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail=f"Simulation session {sim_id} not found.")
    sim = active_simulations[sim_id]
    return {"simulation_id": sim_id, "events": sim.events}

@router.websocket("/ws/{sim_id}")
async def websocket_simulation_stream(websocket: WebSocket, sim_id: str):
    """
    Streams live simulation steps and event telemetry in real-time over WebSocket.
    """
    await websocket.accept()
    if sim_id not in active_simulations:
        await websocket.send_json({"error": f"Simulation {sim_id} not found"})
        await websocket.close()
        return

    sim = active_simulations[sim_id]
    try:
        while not sim.is_completed:
            step_result = sim.step()
            await websocket.send_json(step_result)
            await asyncio.sleep(0.35)  # 350ms playback cadence for smooth visual feedback

        # Send final summary
        summary = sim.get_summary()
        await websocket.send_json({"type": "COMPLETED", "summary": summary})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
