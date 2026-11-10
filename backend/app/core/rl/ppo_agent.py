"""
NETRA Proximal Policy Optimization (PPO) Routing Agent
Implements PyTorch Actor-Critic architecture with Action Masking,
Generalized Advantage Estimation (GAE), and clipped objective optimization.
"""
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

from app.config import settings
from app.core.rl.environment import NetworkRoutingEnv

class ActorCritic(nn.Module):
    def __init__(self, state_dim: int = 43, action_dim: int = 10, hidden_dim: int = 128):
        super(ActorCritic, self).__init__()
        # Shared feature representation
        self.feature_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        
        # Policy Actor head (logits for discrete neighbor selection)
        self.actor_head = nn.Linear(hidden_dim // 2, action_dim)
        
        # Value Critic head (scalar state-value estimate)
        self.critic_head = nn.Linear(hidden_dim // 2, 1)

    def forward(self, state: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        features = self.feature_net(state)
        logits = self.actor_head(features)
        
        # Apply action masking: set masked-out actions to large negative float
        if mask is not None:
            mask = mask.bool()
            logits = logits.masked_fill(~mask, -1e9)
            
        value = self.critic_head(features)
        return logits, value


class PPOAgent:
    def __init__(
        self,
        state_dim: int = 43,
        action_dim: int = 10,
        lr: float = 3e-4,
        gamma: float = 0.98,
        clip_ratio: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        device: str = "cpu"
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.clip_ratio = clip_ratio
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.device = torch.device(device)

        self.learning_rate = lr
        self.policy = ActorCritic(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)

        # A file existing on disk does not imply that a model was trained. Only
        # checkpoints with explicit training metadata are treated as trained.
        self.weights_path = settings.MODEL_WEIGHTS_DIR / "ppo_routing_default.pt"
        self.weights_loaded = False
        self.trained = False
        self.training_episodes = 0
        if self.weights_path.exists():
            self.load_checkpoint(str(self.weights_path))

    def select_action(
        self,
        state: np.ndarray,
        mask: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[int, float, float]:
        """
        Selects an action given observation and legal action mask.
        Returns: action (int), log_prob (float), state_value (float)
        """
        state_t = torch.as_tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
        mask_array = np.asarray(mask, dtype=bool)
        mask_t = torch.as_tensor(mask_array, dtype=torch.bool, device=self.device).unsqueeze(0)

        with torch.no_grad():
            logits, value = self.policy(state_t, mask_t if bool(mask_array.any()) else None)
            probs = torch.softmax(logits, dim=-1)

            # No legal action exists. The environment will convert this into a
            # terminal routing failure; do not silently choose a masked action.
            if not bool(mask_array.any()):
                return 0, 0.0, float(value.item())

            if deterministic:
                action = int(torch.argmax(probs, dim=-1).item())
                # Handle edge case where all logits were masked
                dist = Categorical(probs)
                log_prob = float(dist.log_prob(torch.tensor(action, device=self.device)).item())
            else:
                dist = Categorical(probs)
                action_t = dist.sample()
                action = int(action_t.item())
                log_prob = float(dist.log_prob(action_t).item())

        return action, log_prob, float(value.item())

    def evaluate_route(
        self,
        env: NetworkRoutingEnv,
        max_hops: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluates the PPO policy along an end-to-end route in the environment.
        Strictly measures execution time, hops, path sequence, and cumulative reward.
        """
        start_time = time.perf_counter()
        state = env.reset()
        done = False
        total_reward = 0.0
        step_count = 0
        step_limit = min(env.max_hops, max_hops) if max_hops is not None else env.max_hops

        while not done and step_count < step_limit:
            mask = env.get_action_mask()
            action, _, _ = self.select_action(state, mask, deterministic=True)
            next_state, reward, done, info = env.step(action)
            total_reward += reward
            state = next_state
            step_count += 1

        computation_time = (time.perf_counter() - start_time) * 1000.0

        success = (env.current_node == env.destination)
        return {
            "success": success,
            "path": env.visited_nodes,
            "hops": len(env.visited_nodes) - 1,
            "total_reward": round(total_reward, 3),
            "estimated_delay_ms": round(env.accumulated_delay_ms, 2),
            "computation_time_ms": round(computation_time, 4),
            "algorithm": "ppo_reinforcement_learning",
            "destination_reached": success,
            "reason": None if success else ("Destination unreachable or hop limit" if step_count >= step_limit else "Halted")
        }

    def train_epoch(self, trajectories: List[Dict[str, Any]], epochs: int = 4, batch_size: int = 32) -> Dict[str, float]:
        """
        Performs standard PPO policy and value updates over collected trajectories.
        """
        if not trajectories:
            return {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0}

        states = torch.tensor(np.array([t["state"] for t in trajectories]), dtype=torch.float32, device=self.device)
        actions = torch.tensor([t["action"] for t in trajectories], dtype=torch.long, device=self.device)
        old_log_probs = torch.tensor([t["log_prob"] for t in trajectories], dtype=torch.float32, device=self.device)
        returns = torch.tensor([t["return"] for t in trajectories], dtype=torch.float32, device=self.device)
        advantages = torch.tensor([t["advantage"] for t in trajectories], dtype=torch.float32, device=self.device)
        masks = torch.tensor(np.array([t["mask"] for t in trajectories]), dtype=torch.bool, device=self.device)

        # Normalize advantages
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_loss_val = 0.0
        policy_loss_val = 0.0
        value_loss_val = 0.0

        batch_size = max(1, min(int(batch_size), len(states)))
        update_count = 0
        for _ in range(epochs):
            # Shuffle and update on mini-batches; the previous implementation
            # accepted batch_size but silently performed full-batch updates.
            order = torch.randperm(len(states), device=self.device)
            for batch_indices in order.split(batch_size):
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_returns = returns[batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_masks = masks[batch_indices]

                logits, values = self.policy(batch_states, batch_masks)
                dist = Categorical(logits=logits)
                new_log_probs = dist.log_prob(batch_actions)
                entropy = dist.entropy().mean()

                ratios = torch.exp(new_log_probs - batch_old_log_probs)
                surr1 = ratios * batch_advantages
                surr2 = torch.clamp(ratios, 1.0 - self.clip_ratio, 1.0 + self.clip_ratio) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = nn.MSELoss()(values.squeeze(-1), batch_returns)
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), max_norm=0.5)
                self.optimizer.step()

                total_loss_val += float(loss.item())
                policy_loss_val += float(policy_loss.item())
                value_loss_val += float(value_loss.item())
                update_count += 1

        num_updates = max(1, update_count)
        return {
            "loss": round(total_loss_val / num_updates, 4),
            "policy_loss": round(policy_loss_val / num_updates, 4),
            "value_loss": round(value_loss_val / num_updates, 4)
        }

    def save_checkpoint(self, filepath: str, trained: bool = True, training_episodes: int = 0) -> None:
        """Save weights together with metadata that distinguishes trained policy from initialization."""
        torch.save({
            "state_dict": self.policy.state_dict(),
            "trained": bool(trained),
            "training_episodes": int(training_episodes),
            "architecture_version": 3,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
        }, filepath)
        self.weights_loaded = True
        self.trained = bool(trained)
        self.training_episodes = int(training_episodes)

    def load_checkpoint(self, filepath: str) -> bool:
        """Load only an explicitly versioned checkpoint; ignore legacy random snapshots."""
        if not os.path.exists(filepath):
            return False
        try:
            checkpoint = torch.load(filepath, map_location=self.device, weights_only=True)
            if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint:
                # Older project versions saved raw initialized model weights and
                # incorrectly treated file presence as proof of training.
                return False
            if checkpoint.get("architecture_version") != 3:
                return False
            if checkpoint.get("state_dim") != self.state_dim or checkpoint.get("action_dim") != self.action_dim:
                return False
            self.policy.load_state_dict(checkpoint["state_dict"])
            self.weights_loaded = True
            self.trained = bool(checkpoint.get("trained", False))
            self.training_episodes = int(checkpoint.get("training_episodes", 0))
            return True
        except (OSError, RuntimeError, ValueError, TypeError, KeyError):
            # Keep a fresh policy if the on-disk checkpoint is incompatible or corrupt.
            return False
