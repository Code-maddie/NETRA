"""
NETRA Synthetic Scenario Simulator for DAgger & Residual PPO Training.
Generates multi-topology scenarios with periodic bursts, dynamic link failures,
and noisy controller observations.
"""
from itertools import islice
from typing import Dict, Any, List, Tuple
import numpy as np
import networkx as nx

K_CAND = 4
NF_FLOWS = 8
T_HORIZON = 48
PKT_SIZE = 12.0
N_FEAT = 13


class Scenario:
    pass


def make_scenario(seed: int, n: int = None) -> Scenario:
    rng = np.random.default_rng(seed)
    n = n or int(rng.integers(10, 25))
    fam = str(rng.choice(["er", "ba", "ws"]))
    while True:
        s = int(rng.integers(1 << 30))
        G = {
            "er": lambda: nx.erdos_renyi_graph(n, min(1.0, 4.0 / n), seed=s),
            "ba": lambda: nx.barabasi_albert_graph(n, 2, seed=s),
            "ws": lambda: nx.watts_strogatz_graph(n, 4, 0.3, seed=s)
        }[fam]()
        if nx.is_connected(G):
            break

    E, cap, dly, idx = [], [], [], {}
    for u, v in G.edges():
        c, d = float(rng.choice([10, 40, 100])), float(rng.integers(1, 11))
        for a, b in ((u, v), (v, u)):
            idx[(a, b)] = len(E)
            E.append((a, b))
            cap.append(c)
            dly.append(d)

    nE = len(E)
    pairs = []
    while len(pairs) < NF_FLOWS:
        a, b = rng.choice(n, 2, replace=False)
        pairs.append((int(a), int(b)))

    inc = np.zeros((NF_FLOWS, K_CAND, nE), np.float32)
    valid = np.zeros((NF_FLOWS, K_CAND), bool)
    for f, (a, b) in enumerate(pairs):
        for k, p in enumerate(islice(nx.shortest_simple_paths(G, a, b), K_CAND)):
            valid[f, k] = True
            for x, y in zip(p[:-1], p[1:]):
                inc[f, k, idx[(x, y)]] = 1

    sc = Scenario()
    sc.n, sc.fam, sc.inc, sc.valid = n, fam, inc, valid
    sc.cap, sc.dly = np.array(cap), np.array(dly)

    # Injected link failure window in 50% of scenarios
    alive = np.ones((T_HORIZON, nE), bool)
    if rng.random() < 0.5:
        a, b = list(G.edges())[int(rng.integers(G.number_of_edges()))]
        t0 = int(rng.integers(8, 30))
        t1 = t0 + int(rng.integers(8, 17))
        alive[t0:t1, idx[(a, b)]] = False
        alive[t0:t1, idx[(b, a)]] = False
    sc.alive = alive
    sc.cap_t = np.where(alive, sc.cap, 1e-3)
    sc.ref = np.maximum((inc[:, 0, :] * (sc.dly + PKT_SIZE / sc.cap)).sum(1), 1e-3)

    # Demand generation with periodic bursts
    base = rng.uniform(0.5, 1.5, NF_FLOWS)
    per, ph = rng.choice([8, 12, 16], NF_FLOWS), rng.integers(0, 16, NF_FLOWS)
    wid, amp = rng.integers(3, 7, NF_FLOWS), rng.uniform(2, 5, NF_FLOWS)
    bursty = rng.random(NF_FLOWS) < 0.8
    tt = np.arange(T_HORIZON)[:, None]
    burst = (((tt + ph) % per) < wid) & bursty
    D = base * (1 + amp * burst) * np.exp(rng.normal(0, 0.1, (T_HORIZON, NF_FLOWS)))

    rho = float(rng.choice([0.4, 0.55, 0.7]))
    sc.D = np.tile(D.mean(0), (T_HORIZON, 1))
    sc.Dest = sc.D.copy()
    ch = greedy_choice(sc, 0, np.zeros(NF_FLOWS, int), np.ones((NF_FLOWS, K_CAND), bool) & valid, sweeps=3)
    scale = rho / max(evaluate_scenario(sc, 0, ch, sc.D[0])[2], 1e-6)
    sc.D = D * scale
    sc.Dest = sc.D * np.exp(rng.normal(0, 0.1, (T_HORIZON, NF_FLOWS)))
    sc.Dprior = D.mean(0) * scale
    sc.rho = rho
    return sc


def evaluate_scenario(sc: Scenario, t: int, choice: np.ndarray, D: np.ndarray) -> Tuple[float, float, float, np.ndarray]:
    """Flow-level cost -> (J, weighted loss, MLU, link load)."""
    inc = sc.inc[np.arange(NF_FLOWS), choice]
    cap = sc.cap_t[t]
    load = D @ inc
    u = load / cap
    uc = np.minimum(u, 0.95)
    dl = sc.dly + (PKT_SIZE / cap) * (1 + uc / (2 * (1 - uc)))
    loss = np.clip(1 - cap / np.maximum(load, 1e-9), 0, 0.999)
    fd = inc @ dl
    fl = 1 - np.exp(inc @ np.log1p(-loss))
    w = D / D.sum()
    J = float((w * np.minimum(fd / sc.ref, 50)).sum() + 20 * (w * fl).sum())
    return J, float((w * fl).sum()), float(u[sc.alive[t]].max() if sc.alive[t].any() else u.max()), load


def mask_at(sc: Scenario, t: int) -> np.ndarray:
    m = sc.valid & ((sc.inc @ (~sc.alive[t]).astype(np.float32)) == 0)
    for f in range(NF_FLOWS):
        if not m[f].any():
            m[f, 0] = True
    return m


def greedy_choice(sc: Scenario, t: int, cur: np.ndarray, mask: np.ndarray, sweeps: int = 2, D: np.ndarray = None, stick: float = 0.003) -> np.ndarray:
    """Best-response sweeps. With true D(t) this is the privileged teacher."""
    D = sc.D[t] if D is None else D
    ch = cur.copy()
    for _ in range(sweeps):
        for f in range(NF_FLOWS):
            best, bk = 1e18, ch[f]
            for k in np.flatnonzero(mask[f]):
                c = ch.copy()
                c[f] = k
                J = evaluate_scenario(sc, t, c, D)[0] + stick * (k != cur[f])
                if J < best - 1e-12:
                    best, bk = J, k
            ch[f] = bk
    return ch


class ScenarioEnv:
    def __init__(self, sc: Scenario):
        self.sc = sc
        self.t = 0
        self.U = [np.zeros(len(sc.cap))] * 3
        self.Dh = [sc.Dprior] * 3
        self.cur = np.zeros(NF_FLOWS, int)

    def obs(self) -> Tuple[np.ndarray, np.ndarray]:
        """Measurement state at interval t-1."""
        sc, t = self.sc, self.t
        inc, cap = sc.inc, sc.cap_t[t]
        mask = mask_at(sc, t)
        U1, U2, U3 = self.U
        dh = self.Dh[0]
        own = dh[:, None] * inc[np.arange(NF_FLOWS), self.cur]
        proj = np.maximum(U1[None, None, :] + (dh[:, None, None] * inc - own[:, None, :]) / cap, 0)
        uc = np.minimum(proj, 0.95)
        dl = sc.dly + (PKT_SIZE / cap) * (1 + uc / (2 * (1 - uc)))
        hops = inc.sum(2)
        bott = np.where(inc > 0, cap, 1e9).min(2)

        F = np.stack([
            (inc * U1).max(2),
            (inc * U1).sum(2) / np.maximum(hops, 1),
            (inc * U2).max(2),
            (inc * U3).max(2),
            (inc * proj).max(2),
            np.minimum((inc * dl).sum(2) / sc.ref[:, None], 20) / 5,
            hops / 10,
            np.minimum(bott, 100) / 100,
            (np.arange(K_CAND)[None] == self.cur[:, None]).astype(float),
            np.minimum(dh[:, None] / np.minimum(bott, 1e3), 3),
            np.tile(np.clip(dh / np.maximum(self.Dh[1], 1e-9), 0, 3)[:, None], (1, K_CAND)),
            np.tile(np.clip(dh / np.maximum(self.Dh[2], 1e-9), 0, 3)[:, None], (1, K_CAND)),
            np.full((NF_FLOWS, K_CAND), U1.mean())
        ], -1).astype(np.float32)

        return F, mask

    def peek(self, choice: np.ndarray) -> float:
        return evaluate_scenario(self.sc, self.t, choice, self.sc.D[self.t])[0]

    def step(self, choice: np.ndarray) -> Tuple[float, float, float, float]:
        sc, t = self.sc, self.t
        J, loss, mlu, load = evaluate_scenario(sc, t, choice, sc.D[t])
        ch = float((choice != self.cur).mean())
        self.U = [load / sc.cap_t[t], self.U[0], self.U[1]]
        self.Dh = [sc.Dest[t], self.Dh[0], self.Dh[1]]
        self.cur, self.t = choice.copy(), t + 1
        return J, loss, mlu, ch


def _argmin(score: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.where(mask, score, 1e9).argmin(1)

def h_static(F: np.ndarray, m: np.ndarray) -> np.ndarray:
    return np.where(m[:, 0], 0, m.argmax(1))

def h_leastloaded(F: np.ndarray, m: np.ndarray) -> np.ndarray:
    return _argmin(F[:, :, 0], m)

def h_delay(F: np.ndarray, m: np.ndarray) -> np.ndarray:
    return _argmin(F[:, :, 5], m)

CADJ_ALPHA = 0.02
def h_cadj(F: np.ndarray, m: np.ndarray) -> np.ndarray:
    return _argmin(F[:, :, 5] + CADJ_ALPHA * (1 - F[:, :, 8]), m)

def teacher_ctrl(env: ScenarioEnv, F: np.ndarray, m: np.ndarray) -> np.ndarray:
    return greedy_choice(env.sc, env.t, env.cur, m)

def run_scenario(sc: Scenario, ctrl) -> Dict[str, float]:
    env = ScenarioEnv(sc)
    Js, Ls, Cs = [], [], []
    for _ in range(T_HORIZON):
        F, m = env.obs()
        J, l, u, c = env.step(ctrl(env, F, m))
        Js.append(J)
        Ls.append(l)
        Cs.append(c)
    return {"J": float(np.mean(Js)), "loss": float(np.mean(Ls)), "churn": float(np.mean(Cs))}
