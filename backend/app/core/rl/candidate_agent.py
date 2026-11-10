"""
NETRA Candidate-Path Residual PPO Agent
Implements:
1. Candidate-path decision space (K=4 precomputed loop-free paths, candidate 0 = static Dijkstra).
2. Shared Candidate Scorer MLP (topology-agnostic, 13 normalized path features).
3. Imitation pre-training (Behavioral Cloning / DAgger from teacher).
4. Residual PPO with KL regularization to the BC policy and shadow-baseline reward vs CADJ.
5. Provable Safety Shielding with fallback to hysteresis baseline (CADJ) and fallback telemetry.
"""
import copy
import math
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import networkx as nx
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

from app.config import settings
from app.core.traditional_routing import TraditionalRouter

K_CANDIDATES = 4
N_FEATURES = 13


class CandidatePolicy(nn.Module):
    """
    Topology-agnostic Shared Candidate Scorer.
    Scores any candidate path on any network graph from 13 normalized features.
    """
    def __init__(self, d: int = N_FEATURES, h: int = 64):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Linear(d, h),
            nn.Tanh(),
            nn.Linear(h, h),
            nn.Tanh()
        )
        self.score = nn.Linear(h, 1)
        self.val = nn.Sequential(
            nn.Linear(h, h),
            nn.Tanh(),
            nn.Linear(h, 1)
        )

    def forward(self, x: torch.Tensor, m: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: (batch, NF, K, N_FEATURES) or (batch, K, N_FEATURES)
        m: (batch, NF, K) or (batch, K) bool mask of valid candidates
        returns:
          logits: (batch, NF, K) or (batch, K)
          value: (batch,)
        """
        is_single_flow = (x.ndim == 3)
        if is_single_flow:
            x = x.unsqueeze(1)  # (batch, 1, K, d)
            m = m.unsqueeze(1)  # (batch, 1, K)

        z = self.enc(x)  # (batch, NF, K, h)
        lg = self.score(z).squeeze(-1).masked_fill(~m, -1e9)  # (batch, NF, K)

        m_f = m.unsqueeze(-1).to(torch.float32)  # (batch, NF, K, 1)
        zf = (z * m_f).sum(2) / m_f.sum(2).clamp(min=1.0)  # (batch, NF, h)
        val = self.val(zf.mean(1)).squeeze(-1)  # (batch,)

        if is_single_flow:
            lg = lg.squeeze(1)

        return lg, val


class CandidatePPOAgent:
    """
    Candidate-Path Residual PPO Agent with Shielding and Multi-Step Telemetry.
    """
    def __init__(
        self,
        device: str = "cpu",
        weights_filename: str = "candidate_ppo_residual.pt"
    ):
        self.device = torch.device(device)
        self.k = K_CANDIDATES
        self.feature_dim = N_FEATURES
        self.policy = CandidatePolicy(d=N_FEATURES, h=64).to(self.device)
        self.bc_policy: Optional[CandidatePolicy] = None

        self.weights_path = settings.MODEL_WEIGHTS_DIR / weights_filename
        self.weights_loaded = False
        self.trained = False
        self.training_episodes = 0
        self.best_val_score = 0.0

        # Shielding stats
        self.shield_fallback_count = 0
        self.shield_eval_count = 0

        # Try to load existing checkpoint
        if self.weights_path.exists():
            self.load_checkpoint(str(self.weights_path))

    def extract_features(
        self,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        candidate_paths: List[List[int]],
        link_endpoint_map: Dict[Tuple[int, int], str],
        links_by_id: Dict[str, Dict[str, Any]],
        util_history: List[List[float]],
        demand_history: List[float],
        current_path: Optional[List[int]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the 13 normalized features for each of the K candidate paths.
        Returns:
          F: shape (K, 13) float32
          mask: shape (K,) bool
        """
        F_mat = np.zeros((self.k, self.feature_dim), dtype=np.float32)
        mask = np.zeros(self.k, dtype=bool)

        # Multi-interval utilization snapshots
        U1 = util_history[-1] if len(util_history) >= 1 else [float(l.get("utilization", 0.0)) for l in links]
        U2 = util_history[-2] if len(util_history) >= 2 else U1
        U3 = util_history[-3] if len(util_history) >= 3 else U2

        # Link lookup helper
        link_order = [l["id"] for l in links]
        link_idx_map = {lid: i for i, lid in enumerate(link_order)}

        # Demand history
        dh_curr = demand_history[-1] if demand_history else 60.0
        dh_prev1 = demand_history[-2] if len(demand_history) >= 2 else dh_curr
        dh_prev2 = demand_history[-3] if len(demand_history) >= 3 else dh_prev1

        # Mean network utilization
        mean_u = float(np.mean(U1)) if U1 else 0.0

        # Static reference delay (candidate 0)
        ref_delay = 1.0

        for k_idx, path in enumerate(candidate_paths[:self.k]):
            if not path or len(path) < 2:
                continue

            # Identify links in path
            path_link_objs = []
            path_link_indices = []
            is_active = True

            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                lid = link_endpoint_map.get((min(u, v), max(u, v)))
                if not lid or lid not in links_by_id:
                    is_active = False
                    break
                lobj = links_by_id[lid]
                if lobj.get("status", "active") != "active":
                    is_active = False
                    break
                path_link_objs.append(lobj)
                if lid in link_idx_map:
                    path_link_indices.append(link_idx_map[lid])

            if not is_active or not path_link_objs:
                continue

            mask[k_idx] = True

            # Link metrics along path
            p_u1 = [U1[idx] for idx in path_link_indices] if path_link_indices else [0.0]
            p_u2 = [U2[idx] for idx in path_link_indices] if path_link_indices else [0.0]
            p_u3 = [U3[idx] for idx in path_link_indices] if path_link_indices else [0.0]
            caps = [float(l.get("capacity_mbps", 100.0)) for l in path_link_objs]
            delays = [float(l.get("base_delay_ms", 5.0)) for l in path_link_objs]

            hops = len(path) - 1
            bottleneck_cap = min(caps) if caps else 100.0

            # Projected utilization (removing own load if on path, adding estimated load)
            was_on_this_path = (current_path == path)
            p_proj = []
            for u_val, cap in zip(p_u1, caps):
                own_fraction = (dh_curr / max(cap, 1e-3)) if was_on_this_path else 0.0
                new_load = max(0.0, u_val - own_fraction) + (dh_curr / max(cap, 1e-3))
                p_proj.append(min(0.99, new_load))

            # Projected delay
            proj_delay = 0.0
            for d_base, cap, u_proj in zip(delays, caps, p_proj):
                u_clamped = min(u_proj, 0.95)
                # M/M/1-like delay
                proj_delay += d_base + (12.0 / max(cap, 1.0)) * (1.0 + u_clamped / (2.0 * max(1.0 - u_clamped, 0.05)))

            if k_idx == 0:
                ref_delay = max(proj_delay, 1e-3)

            # Build 13 features
            F_mat[k_idx, 0] = float(max(p_u1))                                    # 0: max util t-1
            F_mat[k_idx, 1] = float(np.mean(p_u1))                                # 1: mean util t-1
            F_mat[k_idx, 2] = float(max(p_u2))                                    # 2: max util t-2
            F_mat[k_idx, 3] = float(max(p_u3))                                    # 3: max util t-3
            F_mat[k_idx, 4] = float(max(p_proj))                                  # 4: max projected util
            F_mat[k_idx, 5] = float(min(proj_delay / max(ref_delay, 1e-3), 20.0) / 5.0)  # 5: delay ratio
            F_mat[k_idx, 6] = float(hops / 10.0)                                  # 6: normalized hops
            F_mat[k_idx, 7] = float(min(bottleneck_cap, 1000.0) / 100.0)          # 7: bottleneck cap
            F_mat[k_idx, 8] = 1.0 if was_on_this_path else 0.0                    # 8: hysteresis flag
            F_mat[k_idx, 9] = float(min(dh_curr / max(bottleneck_cap, 1.0), 3.0)) # 9: demand / bottleneck
            F_mat[k_idx, 10] = float(np.clip(dh_curr / max(dh_prev1, 1e-6), 0.0, 3.0)) # 10: trend t-1/t-2
            F_mat[k_idx, 11] = float(np.clip(dh_curr / max(dh_prev2, 1e-6), 0.0, 3.0)) # 11: trend t-1/t-3
            F_mat[k_idx, 12] = float(mean_u)                                      # 12: network mean util

        # Ensure at least one candidate is unmasked if possible
        if not mask.any() and candidate_paths:
            mask[0] = True

        return F_mat, mask

    def select_candidate(
        self,
        features: np.ndarray,
        mask: np.ndarray,
        greedy: bool = True
    ) -> Tuple[int, float]:
        """
        Selects candidate path index using policy logits.
        """
        if not mask.any():
            return 0, 0.0

        f_t = torch.as_tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
        m_t = torch.as_tensor(mask, dtype=torch.bool, device=self.device).unsqueeze(0)

        with torch.no_grad():
            logits, _ = self.policy(f_t, m_t)
            probs = torch.softmax(logits[0], dim=-1)

            if greedy:
                action = int(torch.argmax(probs).item())
                dist = Categorical(probs)
                log_prob = float(dist.log_prob(torch.tensor(action, device=self.device)).item())
            else:
                dist = Categorical(probs)
                action_t = dist.sample()
                action = int(action_t.item())
                log_prob = float(dist.log_prob(action_t).item())

        return action, log_prob

    def evaluate_route(
        self,
        nodes: List[Dict[str, Any]],
        links: List[Dict[str, Any]],
        source: int,
        destination: int,
        link_endpoint_map: Dict[Tuple[int, int], str],
        links_by_id: Dict[str, Dict[str, Any]],
        util_history: List[List[float]],
        demand_history: List[float],
        current_path: Optional[List[int]] = None,
        shielded: bool = True,
        tau: float = 0.05
    ) -> Dict[str, Any]:
        """
        Evaluates and selects candidate route with optional safety shielding.
        """
        start_time = time.perf_counter()

        # 1. Generate K candidate paths
        candidates = TraditionalRouter.get_candidate_paths(nodes, links, source, destination, k=self.k)
        if not candidates:
            # Fallback to dynamic dijkstra if simple paths couldn't be formed
            trad = TraditionalRouter.compute_route(nodes, links, source, destination, algorithm="dijkstra_dynamic")
            return {
                "success": trad.get("success", False),
                "path": trad.get("path", []),
                "hops": trad.get("hops", 0),
                "candidate_index": 0,
                "shield_fallback": False,
                "computation_time_ms": round((time.perf_counter() - start_time) * 1000.0, 4),
                "algorithm": "ppo_residual"
            }

        # 2. Extract 13 normalized features
        F_mat, mask = self.extract_features(
            nodes=nodes,
            links=links,
            candidate_paths=candidates,
            link_endpoint_map=link_endpoint_map,
            links_by_id=links_by_id,
            util_history=util_history,
            demand_history=demand_history,
            current_path=current_path
        )

        # 3. Policy candidate choice
        chosen_k, _ = self.select_candidate(F_mat, mask, greedy=True)
        chosen_path = candidates[chosen_k] if chosen_k < len(candidates) else candidates[0]
        was_shielded = False

        # 4. Safety Shielding check against hysteresis baseline (CADJ)
        if shielded:
            self.shield_eval_count += 1
            # Baseline decision
            cadj_res = TraditionalRouter.compute_route(
                nodes, links, source, destination,
                algorithm="cadj",
                previous_path=current_path
            )
            cadj_path = cadj_res.get("path", candidates[0])

            # Quick cost estimation of chosen_path vs cadj_path
            def estimate_cost(path_to_check: List[int]) -> float:
                cost = 0.0
                for i in range(len(path_to_check) - 1):
                    lid = link_endpoint_map.get((min(path_to_check[i], path_to_check[i+1]), max(path_to_check[i], path_to_check[i+1])))
                    if lid and lid in links_by_id:
                        lo = links_by_id[lid]
                        u = float(lo.get("utilization", 0.0))
                        b = float(lo.get("base_delay_ms", 5.0))
                        cost += b / (1.0 - min(0.92, u))
                    else:
                        cost += 100.0
                return cost

            c_cost = estimate_cost(chosen_path)
            b_cost = estimate_cost(cadj_path)

            # If RL choice is significantly worse than CADJ by more than tau factor
            if c_cost > (1.0 + tau) * b_cost:
                chosen_path = cadj_path
                chosen_k = -1  # indicates fallback
                was_shielded = True
                self.shield_fallback_count += 1

        computation_time = (time.perf_counter() - start_time) * 1000.0

        return {
            "success": len(chosen_path) >= 2,
            "path": chosen_path,
            "hops": max(0, len(chosen_path) - 1),
            "candidate_index": chosen_k,
            "shield_fallback": was_shielded,
            "computation_time_ms": round(computation_time, 4),
            "algorithm": "ppo_shielded" if shielded else "ppo_residual"
        }

    def save_checkpoint(self, path: Optional[str] = None) -> None:
        save_path = Path(path) if path else self.weights_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "version": "netra_candidate_v2",
            "trained": self.trained,
            "training_episodes": self.training_episodes,
            "best_val_score": self.best_val_score,
            "state_dict": self.policy.state_dict(),
            "timestamp": time.time(),
            "architecture": "Candidate-Path Residual PPO (DAgger + KL + Shield)"
        }, str(save_path))
        self.weights_loaded = True

    def load_checkpoint(self, path: Optional[str] = None) -> bool:
        load_path = Path(path) if path else self.weights_path
        if not load_path.exists():
            return False
        try:
            ckpt = torch.load(str(load_path), map_location=self.device)
            if isinstance(ckpt, dict) and "state_dict" in ckpt:
                self.policy.load_state_dict(ckpt["state_dict"])
                self.trained = bool(ckpt.get("trained", False))
                self.training_episodes = int(ckpt.get("training_episodes", 0))
                self.best_val_score = float(ckpt.get("best_val_score", 0.0))
                self.weights_loaded = True
                return True
        except Exception:
            return False
        return False

    def train_dagger_and_ppo(
        self,
        dagger_iters: int = 3,
        dagger_eps: int = 8,
        ppo_iters: int = 15,
        ppo_eps: int = 6,
        val_count: int = 8,
        seed: int = 42,
        log_callback = print
    ) -> Dict[str, Any]:
        """
        Executes end-to-end training:
        1. DAgger imitation pre-training from privileged teacher.
        2. Cloned BC policy reference.
        3. KL-regularized Residual PPO against CADJ shadow baseline.
        4. VAL-only model checkpoint selection.
        """
        from app.core.rl.scenario_sim import make_scenario, ScenarioEnv, teacher_ctrl, h_cadj, run_scenario

        rng = np.random.default_rng(seed)
        seeds_iter = iter(range(seed * 1000, seed * 1000 + 100000))
        val_seeds = [seed * 1000 + 50000 + i for i in range(val_count)]

        # --- 1. DAgger Imitation Learning ---
        X, M, Y = [], [], []
        opt = torch.optim.Adam(self.policy.parameters(), lr=1e-3)
        log_callback(f"[DAgger] Beginning {dagger_iters} DAgger iterations ({dagger_eps} episodes each)...")

        for it in range(dagger_iters):
            beta = [1.0, 0.5, 0.2, 0.0][min(it, 3)]
            for _ in range(dagger_eps):
                sc = make_scenario(next(seeds_iter))
                env = ScenarioEnv(sc)
                for _ in range(48):
                    F_obs, m_obs = env.obs()
                    y = teacher_ctrl(env, F_obs, m_obs)
                    X.append(F_obs)
                    M.append(m_obs)
                    Y.append(y)
                    # Learner-visited rollout
                    if rng.random() < beta:
                        env.step(y)
                    else:
                        with torch.no_grad():
                            lg, _ = self.policy(torch.from_numpy(F_obs)[None].to(self.device), torch.from_numpy(m_obs)[None].to(self.device))
                            env.step(lg[0].argmax(-1).cpu().numpy())

            Xt = torch.tensor(np.stack(X), dtype=torch.float32, device=self.device)
            Mt = torch.tensor(np.stack(M), dtype=torch.bool, device=self.device)
            Yt = torch.tensor(np.stack(Y), dtype=torch.long, device=self.device)

            for epoch in range(15):
                perm = torch.randperm(len(Xt))
                for i in range(0, len(perm), 128):
                    b = perm[i:i + 128]
                    lg, _ = self.policy(Xt[b], Mt[b])
                    loss = F.cross_entropy(lg.reshape(-1, self.k), Yt[b].reshape(-1))
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
            log_callback(f"[DAgger {it + 1}/{dagger_iters}] Samples: {len(Xt)}, Cross-Entropy Loss: {loss.item():.4f}")

        # Clone BC policy for KL regularization
        self.bc_policy = copy.deepcopy(self.policy)

        # Validation scoring helper
        def compute_val_score(pol_net) -> float:
            def act_fn(env, F_o, m_o):
                with torch.no_grad():
                    lg, _ = pol_net(torch.from_numpy(F_o)[None].to(self.device), torch.from_numpy(m_o)[None].to(self.device))
                    return lg[0].argmax(-1).cpu().numpy()
            costs_pol = [run_scenario(make_scenario(s), lambda e, F, m: act_fn(e, F, m))["J"] for s in val_seeds]
            costs_cadj = [run_scenario(make_scenario(s), lambda e, F, m: h_cadj(F, m))["J"] for s in val_seeds]
            return float(np.mean((np.array(costs_pol) - np.array(costs_cadj)) / np.array(costs_cadj)))

        best_score = compute_val_score(self.policy)
        best_sd = copy.deepcopy(self.policy.state_dict())
        log_callback(f"[PPO] Initial BC policy relative cost vs CADJ on VAL: {best_score * 100:+.2f}%")

        # --- 2. Residual PPO with KL Regularization ---
        ppo_opt = torch.optim.Adam(self.policy.parameters(), lr=3e-4)

        for it in range(ppo_iters):
            beta_kl = 0.2 + (0.02 - 0.2) * (it / max(ppo_iters - 1, 1))
            Xs, Ms, As, LPs, Rs, Ads, Rets = [], [], [], [], [], [], []

            for _ in range(ppo_eps):
                sc = make_scenario(next(seeds_iter))
                env = ScenarioEnv(sc)
                x_, m_, a_, lp_, r_, v_ = [], [], [], [], [], []

                for _ in range(48):
                    F_obs, m_obs = env.obs()
                    f_t = torch.from_numpy(F_obs)[None].to(self.device)
                    m_t = torch.from_numpy(m_obs)[None].to(self.device)
                    with torch.no_grad():
                        lg, val = self.policy(f_t, m_t)
                        dist = Categorical(logits=lg[0])
                        action_sample = dist.sample()
                        lp = dist.log_prob(action_sample).sum()

                    J_shadow = env.peek(h_cadj(F_obs, m_obs))
                    J_curr, _, _, churn = env.step(action_sample.cpu().numpy())
                    reward = float(np.clip(-(J_curr - J_shadow) / max(J_shadow, 1e-6) - 0.1 * churn, -5.0, 5.0))

                    x_.append(F_obs)
                    m_.append(m_obs)
                    a_.append(action_sample.cpu().numpy())
                    lp_.append(lp.item())
                    r_.append(reward)
                    v_.append(val.item())

                # GAE returns and advantages
                adv = np.zeros(48)
                last_adv = 0.0
                for t in reversed(range(48)):
                    next_val = v_[t + 1] if t + 1 < 48 else 0.0
                    delta = r_[t] + 0.95 * next_val - v_[t]
                    last_adv = delta + 0.95 * 0.95 * last_adv
                    adv[t] = last_adv

                Xs += x_; Ms += m_; As += a_; LPs += lp_; Rs += r_; Ads += list(adv); Rets += list(adv + np.array(v_))

            X_t = torch.tensor(np.stack(Xs), dtype=torch.float32, device=self.device)
            M_t = torch.tensor(np.stack(Ms), dtype=torch.bool, device=self.device)
            A_t = torch.tensor(np.stack(As), dtype=torch.long, device=self.device)
            LP_t = torch.tensor(LPs, dtype=torch.float32, device=self.device)
            AD_t = torch.tensor(Ads, dtype=torch.float32, device=self.device)
            RT_t = torch.tensor(Rets, dtype=torch.float32, device=self.device)

            if len(AD_t) > 1:
                AD_t = (AD_t - AD_t.mean()) / (AD_t.std() + 1e-8)

            with torch.no_grad():
                ref_lg, _ = self.bc_policy(X_t, M_t)
                ref_lp = F.log_softmax(ref_lg, dim=-1)

            for _ in range(4):
                perm = torch.randperm(len(X_t))
                for i in range(0, len(perm), 128):
                    b = perm[i:i + 128]
                    lg, v = self.policy(X_t[b], M_t[b])
                    lsm = F.log_softmax(lg, dim=-1)
                    lp = lsm.gather(-1, A_t[b].unsqueeze(-1)).squeeze(-1).sum(1)
                    ratio = torch.exp(lp - LP_t[b])

                    pg_loss = -torch.min(ratio * AD_t[b], ratio.clamp(0.8, 1.2) * AD_t[b]).mean()
                    vf_loss = 0.5 * ((v - RT_t[b]) ** 2).mean()

                    # Masked KL
                    kl_elem = torch.where(M_t[b], ref_lp[b].exp() * (ref_lp[b] - lsm), torch.zeros_like(lsm))
                    kl_val = kl_elem.sum(-1).sum(-1).mean()

                    # Masked entropy
                    p = lsm.exp()
                    ent_elem = -p * torch.where(M_t[b] & (p > 1e-12), lsm, torch.zeros_like(lsm))
                    ent_val = ent_elem.sum(-1).mean()

                    total_loss = pg_loss + vf_loss + beta_kl * kl_val - 0.003 * ent_val
                    ppo_opt.zero_grad()
                    total_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
                    ppo_opt.step()

            vs = compute_val_score(self.policy)
            mean_r = float(np.mean(Rs)) if Rs else 0.0
            log_callback(f"[PPO {it + 1}/{ppo_iters}] Mean Reward vs CADJ: {mean_r:+.3f}, VAL relative cost: {vs * 100:+.2f}%")
            if vs < best_score:
                best_score = vs
                best_sd = copy.deepcopy(self.policy.state_dict())

        # Select best checkpoint (VAL-only discipline)
        self.policy.load_state_dict(best_sd)
        self.trained = True
        self.training_episodes = dagger_iters * dagger_eps + ppo_iters * ppo_eps
        self.best_val_score = float(best_score)
        self.save_checkpoint()

        log_callback(f"[Training Complete] Selected checkpoint best VAL rel.cost vs CADJ: {best_score * 100:+.2f}%. Saved to {self.weights_path}.")

        return {
            "success": True,
            "dagger_episodes": dagger_iters * dagger_eps,
            "ppo_episodes": ppo_iters * ppo_eps,
            "total_episodes": self.training_episodes,
            "best_val_score_pct": round(self.best_val_score * 100.0, 2),
            "weights_file": str(self.weights_path)
        }
