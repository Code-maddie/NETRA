"""Reinforcement-learning status and training endpoints."""
import copy
from pathlib import Path
import random
from typing import Optional, Dict, Any, List

import numpy as np
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.rl.ppo_agent import PPOAgent
from app.core.rl.candidate_agent import CandidatePPOAgent
from app.core.rl.environment import NetworkRoutingEnv
from app.core.topology import generate_topology
from app.core.validator import NetworkValidator

router = APIRouter(prefix="/rl", tags=["Reinforcement Learning"])

# Shared policies
global_ppo_agent = PPOAgent()
global_candidate_agent = CandidatePPOAgent()


@router.get("/checkpoints")
def api_get_rl_checkpoints():
    weights_dir = Path(settings.MODEL_WEIGHTS_DIR)
    weights = []
    if weights_dir.exists():
        for path in sorted(weights_dir.glob("*.pt")):
            weights.append({
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "available": True,
            })
    return {
        "checkpoints": weights,
        "active_candidate_trained": global_candidate_agent.trained,
        "active_legacy_trained": global_ppo_agent.trained,
    }


class TrainPPORequest(BaseModel):
    episodes: int = Field(default=30, ge=1, le=200, description="Training episodes")
    mode: str = Field(default="residual", description="residual (Candidate DAgger+PPO) or legacy (Per-Hop PPO)")
    node_count: int = Field(default=20, ge=2, le=100)
    learning_rate: Optional[float] = Field(default=3e-4, gt=0.0, le=0.01)
    topology_data: Optional[Dict[str, Any]] = None
    source: Optional[int] = None
    destination: Optional[int] = None
    seed: int = 42


@router.get("/status")
def api_get_rl_status():
    """Report model initialization and training metadata for Candidate Residual PPO and Legacy PPO."""
    c_total = sum(p.numel() for p in global_candidate_agent.policy.parameters())
    c_trainable = sum(p.numel() for p in global_candidate_agent.policy.parameters() if p.requires_grad)

    l_total = sum(p.numel() for p in global_ppo_agent.policy.parameters())
    l_trainable = sum(p.numel() for p in global_ppo_agent.policy.parameters() if p.requires_grad)

    return {
        "algorithm": "NETRA V3 Candidate-Path Residual PPO",
        "architecture": "Shared Candidate Scorer MLP (13 features, DAgger + Residual PPO + Shield)",
        "state_dimension": global_candidate_agent.feature_dim,
        "action_dimension": global_candidate_agent.k,
        "total_parameters": c_total,
        "trainable_parameters": c_trainable,
        "device": str(global_candidate_agent.device),
        "weights_file": str(global_candidate_agent.weights_path),
        "weights_loaded": global_candidate_agent.weights_loaded,
        "trained": global_candidate_agent.trained,
        "training_episodes": global_candidate_agent.training_episodes,
        "best_val_score_pct": round(global_candidate_agent.best_val_score * 100.0, 2),
        "legacy_ppo": {
            "algorithm": "Legacy Per-Hop PPO",
            "weights_loaded": global_ppo_agent.weights_loaded,
            "trained": global_ppo_agent.trained,
            "training_episodes": global_ppo_agent.training_episodes,
            "total_parameters": l_total
        }
    }


@router.post("/train")
def api_train_rl(req: TrainPPORequest):
    """Train PPO: defaults to Candidate Residual PPO with DAgger imitation & KL-regularized PPO."""
    if req.mode == "residual":
        # Run candidate DAgger + Residual PPO training
        dagger_it = max(2, min(4, req.episodes // 20))
        dagger_ep = max(3, min(8, req.episodes // 8))
        ppo_it = max(3, min(15, req.episodes // 4))
        ppo_ep = max(3, min(6, req.episodes // 8))
        res = global_candidate_agent.train_dagger_and_ppo(
            dagger_iters=dagger_it,
            dagger_eps=dagger_ep,
            ppo_iters=ppo_it,
            ppo_eps=ppo_ep,
            val_count=8,
            seed=req.seed
        )
        return {
            "success": True,
            "mode": "residual",
            "episodes_trained": res["total_episodes"],
            "dagger_episodes": res["dagger_episodes"],
            "ppo_episodes": res["ppo_episodes"],
            "best_val_score_pct": res["best_val_score_pct"],
            "weights_file": res["weights_file"],
            "mean_reward": f"VAL cost vs CADJ: {res['best_val_score_pct']:+.1f}%",
            "successful_episodes_before_update": res["total_episodes"]
        }

    # Legacy per-hop training mode
    try:
        rng = random.Random(req.seed)
        np.random.seed(req.seed)
        torch.manual_seed(req.seed)

        if req.learning_rate is not None:
            for group in global_ppo_agent.optimizer.param_groups:
                group["lr"] = req.learning_rate
            global_ppo_agent.learning_rate = req.learning_rate

        if req.topology_data is not None:
            base_topology = copy.deepcopy(req.topology_data)
            if not base_topology.get("nodes") or not isinstance(base_topology.get("links"), list):
                raise HTTPException(status_code=400, detail="topology_data must contain nodes and links arrays")
        else:
            base_topology = generate_topology(
                node_count=req.node_count,
                topology_type="random",
                density="medium",
                seed=req.seed,
            )

        nodes = base_topology["nodes"]
        node_ids = [int(n["id"]) for n in nodes]
        node_id_set = set(node_ids)
        if len(node_ids) < 2:
            raise HTTPException(status_code=400, detail="Training requires at least two nodes")

        if (req.source is None) != (req.destination is None):
            raise HTTPException(status_code=400, detail="Provide both source and destination, or neither")
        if req.source is not None:
            if req.source not in node_id_set or req.destination not in node_id_set:
                raise HTTPException(status_code=400, detail="Training endpoints must exist in the supplied topology")
            if req.source == req.destination:
                raise HTTPException(status_code=400, detail="Source and destination must be different")
            validation = NetworkValidator.validate_network_and_endpoints(
                base_topology, source=int(req.source), destination=int(req.destination)
            )
            if not validation.get("valid"):
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Training endpoints are not connected in this topology", "errors": validation.get("errors", [])},
                )

        trajectories: List[Dict[str, Any]] = []
        episode_rewards: List[float] = []
        successful_episodes = 0

        for ep in range(req.episodes):
            episode_topology = copy.deepcopy(base_topology)
            # Train on a range of link conditions. Random hot links force the
            # policy to consider utilization rather than only base propagation delay.
            for link in episode_topology["links"]:
                link["status"] = "active"
                if rng.random() < 0.20:
                    link["utilization"] = round(rng.uniform(0.72, 0.94), 3)
                else:
                    link["utilization"] = round(rng.uniform(0.03, 0.48), 3)

            if req.source is not None:
                source, dest = int(req.source), int(req.destination)
            else:
                source = node_ids[ep % len(node_ids)]
                dest = node_ids[(ep + max(1, len(node_ids) // 2)) % len(node_ids)]
                if source == dest:
                    dest = node_ids[(ep + 1) % len(node_ids)]

            env = NetworkRoutingEnv(
                episode_topology["nodes"], episode_topology["links"],
                source=source, destination=dest,
                max_hops=max(1, len(node_ids) - 1),
            )
            state = env.reset()
            done = False
            ep_reward = 0.0
            episode_steps = 0
            ep_states, ep_actions, ep_log_probs = [], [], []
            ep_rewards, ep_masks, ep_values = [], [], []

            while not done:
                mask = env.get_action_mask()
                action, log_prob, value = global_ppo_agent.select_action(
                    state, mask, deterministic=False
                )
                next_state, reward, done, info = env.step(action)
                ep_states.append(state)
                ep_actions.append(action)
                ep_log_probs.append(log_prob)
                ep_rewards.append(float(reward))
                ep_masks.append(mask)
                ep_values.append(value)
                state = next_state
                ep_reward += float(reward)
                episode_steps += 1
                if episode_steps > env.max_hops + 1:
                    raise RuntimeError("Routing environment failed to terminate within its hop limit")

            if info.get("success", env.current_node == dest):
                successful_episodes += 1
            episode_rewards.append(round(ep_reward, 3))

            # Generalized Advantage Estimation (GAE). Episodes terminate at a
            # destination or a no-route state, so the bootstrap value is zero.
            advantages = [0.0] * len(ep_rewards)
            gae = 0.0
            for i in reversed(range(len(ep_rewards))):
                next_value = ep_values[i + 1] if i + 1 < len(ep_values) else 0.0
                delta = ep_rewards[i] + global_ppo_agent.gamma * next_value - ep_values[i]
                gae = delta + global_ppo_agent.gamma * 0.95 * gae
                advantages[i] = gae
            returns = [adv + val for adv, val in zip(advantages, ep_values)]

            for i in range(len(ep_states)):
                trajectories.append({
                    "state": ep_states[i],
                    "action": ep_actions[i],
                    "log_prob": ep_log_probs[i],
                    "return": returns[i],
                    "advantage": advantages[i],
                    "mask": ep_masks[i],
                })

        metrics = global_ppo_agent.train_epoch(trajectories, epochs=4)
        global_ppo_agent.save_checkpoint(
            str(global_ppo_agent.weights_path), trained=True,
            training_episodes=global_ppo_agent.training_episodes + req.episodes,
        )

        return {
            "success": True,
            "episodes_trained": req.episodes,
            "successful_episodes_before_update": successful_episodes,
            "trajectories_collected": len(trajectories),
            "mean_reward": round(float(np.mean(episode_rewards)), 3) if episode_rewards else 0.0,
            "reward_history": episode_rewards,
            "training_metrics": metrics,
            "trained_on_supplied_topology": req.topology_data is not None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPO training failed: {str(e)}")
