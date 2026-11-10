"""NETRA V2: candidate-path, imitation-initialised, KL-regularised residual PPO.
Run:  python netra_v2.py --tier smoke|dev|full
"""
import argparse, copy
from itertools import islice
import numpy as np
import networkx as nx

K, NF, T, PKT, NFEAT = 4, 8, 48, 12.0, 13


class Sc: pass


def make_scenario(seed, n=None):
    rng = np.random.default_rng(seed)
    n = n or int(rng.integers(10, 25))
    fam = str(rng.choice(["er", "ba", "ws"]))
    while True:
        s = int(rng.integers(1 << 30))
        G = {"er": lambda: nx.erdos_renyi_graph(n, min(1.0, 4.0 / n), seed=s),
             "ba": lambda: nx.barabasi_albert_graph(n, 2, seed=s),
             "ws": lambda: nx.watts_strogatz_graph(n, 4, 0.3, seed=s)}[fam]()
        if nx.is_connected(G):
            break
    E, cap, dly, idx = [], [], [], {}
    for u, v in G.edges():
        c, d = float(rng.choice([10, 40, 100])), float(rng.integers(1, 11))
        for a, b in ((u, v), (v, u)):
            idx[(a, b)] = len(E); E.append((a, b)); cap.append(c); dly.append(d)
    nE = len(E)
    pairs = []
    while len(pairs) < NF:
        a, b = rng.choice(n, 2, replace=False); pairs.append((int(a), int(b)))
    inc = np.zeros((NF, K, nE), np.float32); valid = np.zeros((NF, K), bool)
    for f, (a, b) in enumerate(pairs):
        for k, p in enumerate(islice(nx.shortest_simple_paths(G, a, b), K)):  # k=0 is static Dijkstra
            valid[f, k] = True
            for x, y in zip(p[:-1], p[1:]):
                inc[f, k, idx[(x, y)]] = 1
    sc = Sc()
    sc.n, sc.fam, sc.inc, sc.valid = n, fam, inc, valid
    sc.cap, sc.dly = np.array(cap), np.array(dly)
    alive = np.ones((T, nE), bool)                       # one link failure window in 50% of scenarios
    if rng.random() < 0.5:
        a, b = list(G.edges())[int(rng.integers(G.number_of_edges()))]
        t0 = int(rng.integers(8, 30)); t1 = t0 + int(rng.integers(8, 17))
        alive[t0:t1, idx[(a, b)]] = False; alive[t0:t1, idx[(b, a)]] = False
    sc.alive = alive
    sc.cap_t = np.where(alive, sc.cap, 1e-3)
    sc.ref = np.maximum((inc[:, 0, :] * (sc.dly + PKT / sc.cap)).sum(1), 1e-3)
    base = rng.uniform(0.5, 1.5, NF)
    per, ph = rng.choice([8, 12, 16], NF), rng.integers(0, 16, NF)
    wid, amp = rng.integers(3, 7, NF), rng.uniform(2, 5, NF)
    bursty = rng.random(NF) < 0.8
    tt = np.arange(T)[:, None]
    burst = (((tt + ph) % per) < wid) & bursty
    D = base * (1 + amp * burst) * np.exp(rng.normal(0, .1, (T, NF)))
    rho = float(rng.choice([.4, .55, .7]))
    sc.D = np.tile(D.mean(0), (T, 1)); sc.Dest = sc.D.copy()      # calibrate on mean demand
    ch = greedy_choice(sc, 0, np.zeros(NF, int), np.ones((NF, K), bool) & valid, sweeps=3)
    scale = rho / max(evaluate(sc, 0, ch, sc.D[0])[2], 1e-6)
    sc.D = D * scale
    sc.Dest = sc.D * np.exp(rng.normal(0, .1, (T, NF)))           # noisy measurement the controller sees
    sc.Dprior = D.mean(0) * scale
    sc.rho = rho
    return sc


def evaluate(sc, t, choice, D):
    """Flow-level cost of a joint path choice -> (J, weighted loss, MLU, link load)."""
    inc = sc.inc[np.arange(NF), choice]
    cap = sc.cap_t[t]
    load = D @ inc
    u = load / cap
    uc = np.minimum(u, .95)
    dl = sc.dly + (PKT / cap) * (1 + uc / (2 * (1 - uc)))
    loss = np.clip(1 - cap / np.maximum(load, 1e-9), 0, .999)
    fd = inc @ dl
    fl = 1 - np.exp(inc @ np.log1p(-loss))
    w = D / D.sum()
    J = float((w * np.minimum(fd / sc.ref, 50)).sum() + 20 * (w * fl).sum())
    return J, float((w * fl).sum()), float(u[sc.alive[t]].max() if sc.alive[t].any() else u.max()), load


def mask_at(sc, t):
    m = sc.valid & ((sc.inc @ (~sc.alive[t]).astype(np.float32)) == 0)
    for f in range(NF):
        if not m[f].any():
            m[f, 0] = True
    return m


def greedy_choice(sc, t, cur, mask, sweeps=2, D=None, stick=0.003):
    """Best-response sweeps. With true D(t) this is the PRIVILEGED teacher (training only)."""
    D = sc.D[t] if D is None else D
    ch = cur.copy()
    for _ in range(sweeps):
        for f in range(NF):
            best, bk = 1e18, ch[f]
            for k in np.flatnonzero(mask[f]):
                c = ch.copy(); c[f] = k
                J = evaluate(sc, t, c, D)[0] + stick * (k != cur[f])
                if J < best - 1e-12:
                    best, bk = J, k
            ch[f] = bk
    return ch


class Env:
    def __init__(s, sc):
        s.sc, s.t = sc, 0
        s.U = [np.zeros(len(sc.cap))] * 3
        s.Dh = [sc.Dprior] * 3
        s.cur = np.zeros(NF, int)

    def obs(s):
        """ONLY interval t-1 measurements (+ link status at t). Never D(t)."""
        sc, t = s.sc, s.t
        inc, cap = sc.inc, sc.cap_t[t]
        mask = mask_at(sc, t)
        U1, U2, U3 = s.U
        dh = s.Dh[0]
        own = dh[:, None] * inc[np.arange(NF), s.cur]
        proj = np.maximum(U1[None, None, :] + (dh[:, None, None] * inc - own[:, None, :]) / cap, 0)
        uc = np.minimum(proj, .95)
        dl = sc.dly + (PKT / cap) * (1 + uc / (2 * (1 - uc)))
        hops = inc.sum(2)
        bott = np.where(inc > 0, cap, 1e9).min(2)
        F = np.stack([
            (inc * U1).max(2), (inc * U1).sum(2) / np.maximum(hops, 1), (inc * U2).max(2), (inc * U3).max(2),
            (inc * proj).max(2), np.minimum((inc * dl).sum(2) / sc.ref[:, None], 20) / 5, hops / 10,
            np.minimum(bott, 100) / 100, (np.arange(K)[None] == s.cur[:, None]).astype(float),
            np.minimum(dh[:, None] / np.minimum(bott, 1e3), 3),
            np.tile(np.clip(dh / np.maximum(s.Dh[1], 1e-9), 0, 3)[:, None], (1, K)),
            np.tile(np.clip(dh / np.maximum(s.Dh[2], 1e-9), 0, 3)[:, None], (1, K)),
            np.full((NF, K), U1.mean())], -1).astype(np.float32)
        return F, mask

    def peek(s, choice):
        return evaluate(s.sc, s.t, choice, s.sc.D[s.t])[0]

    def step(s, choice):
        sc, t = s.sc, s.t
        J, loss, mlu, load = evaluate(sc, t, choice, sc.D[t])
        ch = float((choice != s.cur).mean())
        s.U = [load / sc.cap_t[t], s.U[0], s.U[1]]
        s.Dh = [sc.Dest[t], s.Dh[0], s.Dh[1]]
        s.cur, s.t = choice.copy(), t + 1
        return J, loss, mlu, ch


# ---- observation-only heuristics (your 4 baselines' analogues + the strong one)
def _argmin(score, mask): return np.where(mask, score, 1e9).argmin(1)
def h_static(F, m): return np.where(m[:, 0], 0, m.argmax(1))
def h_leastloaded(F, m): return _argmin(F[:, :, 0], m)
def h_delay(F, m): return _argmin(F[:, :, 5], m)
CADJ_A = 0.02
def h_cadj(F, m): return _argmin(F[:, :, 5] + CADJ_A * (1 - F[:, :, 8]), m)


def tune_cadj(seeds, grid=(0, .005, .01, .02, .05, .1, .2)):
    global CADJ_A
    best = None
    for a in grid:
        CADJ_A = a
        j = np.mean([run(make_scenario(s), lambda e, F, m: h_cadj(F, m))["J"] for s in seeds])
        if best is None or j < best[0]: best = (j, a)
    CADJ_A = best[1]; return best[1]


def run(sc, ctrl):
    env = Env(sc); Js, Ls, Cs = [], [], []
    for _ in range(T):
        F, m = env.obs()
        J, l, u, c = env.step(ctrl(env, F, m))
        Js.append(J); Ls.append(l); Cs.append(c)
    return dict(J=np.mean(Js), loss=np.mean(Ls), churn=np.mean(Cs))


def teacher_ctrl(env, F, m): return greedy_choice(env.sc, env.t, env.cur, m)   # privileged, NOT deployable


def paired_report(res, ref, name, rng=np.random.default_rng(0)):
    a, b = np.array(res[name]), np.array(res[ref])
    rel = (a - b) / b
    bs = [np.mean(rel[rng.integers(0, len(rel), len(rel))]) for _ in range(5000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    w = int((rel < -.01).sum()); l = int((rel > .01).sum()); tie = len(rel) - w - l
    return (f"{name:>14} vs {ref:<12} rel.cost mean {rel.mean()*100:+6.1f}% [{lo*100:+6.1f},{hi*100:+6.1f}] "
            f"median {np.median(rel)*100:+6.1f}%  W/T/L {w}/{tie}/{l}")


def build_torch():
    import torch, torch.nn as nn, torch.nn.functional as Fn

    class Pol(nn.Module):
        """Shared candidate scorer: one MLP scores every candidate of every flow, any topology."""
        def __init__(s, d=NFEAT, h=64):
            super().__init__()
            s.enc = nn.Sequential(nn.Linear(d, h), nn.Tanh(), nn.Linear(h, h), nn.Tanh())
            s.score = nn.Linear(h, 1)
            s.val = nn.Sequential(nn.Linear(h, h), nn.Tanh(), nn.Linear(h, 1))

        def forward(s, x, m):
            z = s.enc(x)
            lg = s.score(z).squeeze(-1).masked_fill(~m, -1e9)
            m_f = m.unsqueeze(-1).to(torch.float32)
            zf = (z * m_f).sum(2) / m_f.sum(2).clamp(min=1.0)
            return lg, s.val(zf.mean(1)).squeeze(-1)

    def act(pol, F, m, greedy=True):                    # evaluation is ALWAYS argmax
        with torch.no_grad():
            lg, _ = pol(torch.from_numpy(F)[None], torch.from_numpy(m)[None])
            return lg[0].argmax(-1).numpy() if greedy else torch.distributions.Categorical(logits=lg[0]).sample().numpy()

    def dagger(pol, seeds, iters=4, eps=30, epochs=25, log=print):
        X, M, Y = [], [], []
        opt = torch.optim.Adam(pol.parameters(), 1e-3)
        rng = np.random.default_rng(1)
        for it in range(iters):
            beta = [1.0, .5, .2, 0.0][min(it, 3)]
            for _ in range(eps):
                env = Env(make_scenario(next(seeds)))
                for _ in range(T):
                    F, m = env.obs(); y = teacher_ctrl(env, F, m)
                    X.append(F); M.append(m); Y.append(y)
                    env.step(y if rng.random() < beta else act(pol, F, m))   # learner-visited states
            Xt, Mt, Yt = torch.tensor(np.stack(X)), torch.tensor(np.stack(M)), torch.tensor(np.stack(Y), dtype=torch.long)
            for _ in range(epochs):
                perm = torch.randperm(len(Xt))
                for i in range(0, len(perm), 256):
                    b = perm[i:i + 256]
                    lg, _ = pol(Xt[b], Mt[b])
                    loss = Fn.cross_entropy(lg.reshape(-1, K), Yt[b].reshape(-1))
                    opt.zero_grad(); loss.backward(); opt.step()
            log(f"[DAgger {it}] data={len(Xt)} last CE={loss.item():.4f}")

    def val_score(pol, seeds):
        a = [run(make_scenario(s), lambda e, F, m: act(pol, F, m))["J"] for s in seeds]
        b = [run(make_scenario(s), lambda e, F, m: h_cadj(F, m))["J"] for s in seeds]
        return float(np.mean((np.array(a) - np.array(b)) / np.array(b)))

    def ppo(pol, ref, seeds, val_seeds, iters=60, neps=16, log=print):
        opt = torch.optim.Adam(pol.parameters(), 3e-4)
        best, best_sd = val_score(pol, val_seeds), copy.deepcopy(pol.state_dict())
        log(f"[PPO] start (BC) val rel.cost vs cadj = {best*100:+.2f}%")
        for it in range(iters):
            beta_kl = 0.2 + (0.02 - 0.2) * it / max(iters - 1, 1)
            Xs, Ms, As, LPs, Rs, Ads, Rets = [], [], [], [], [], [], []
            for _ in range(neps):
                env = Env(make_scenario(next(seeds)))
                x_, m_, a_, lp_, r_, v_ = [], [], [], [], [], []
                for _ in range(T):
                    F, m = env.obs()
                    with torch.no_grad():
                        lg, v = pol(torch.from_numpy(F)[None], torch.from_numpy(m)[None])
                        d = torch.distributions.Categorical(logits=lg[0]); a = d.sample()
                        lp = d.log_prob(a).sum()
                    Jb = env.peek(h_cadj(F, m))                       # shadow baseline, same state
                    J, _, _, ch = env.step(a.numpy())
                    r = float(np.clip(-(J - Jb) / Jb - 0.1 * ch, -5, 5))
                    x_.append(F); m_.append(m); a_.append(a.numpy()); lp_.append(lp.item()); r_.append(r); v_.append(v.item())
                adv, last = np.zeros(T), 0.0
                for t in reversed(range(T)):
                    nv = v_[t + 1] if t + 1 < T else 0.0
                    last = (r_[t] + 0.95 * nv - v_[t]) + 0.95 * 0.95 * last; adv[t] = last
                Xs += x_; Ms += m_; As += a_; LPs += lp_; Rs += r_; Ads += list(adv); Rets += list(adv + np.array(v_))
            X, M, A = torch.tensor(np.stack(Xs)), torch.tensor(np.stack(Ms)), torch.tensor(np.stack(As), dtype=torch.long)
            LP, AD, RT = (torch.tensor(v, dtype=torch.float32) for v in (LPs, Ads, Rets))
            AD = (AD - AD.mean()) / (AD.std() + 1e-8)
            with torch.no_grad():
                ref_lg = ref(X, M)[0]
                ref_lp = torch.log_softmax(ref_lg, -1)
            for _ in range(4):
                perm = torch.randperm(len(X))
                for i in range(0, len(perm), 128):
                    b = perm[i:i + 128]
                    lg, v = pol(X[b], M[b]); lsm = torch.log_softmax(lg, -1)
                    lp = lsm.gather(-1, A[b].unsqueeze(-1)).squeeze(-1).sum(1)
                    ratio = torch.exp(lp - LP[b])
                    pg = -torch.min(ratio * AD[b], ratio.clamp(.8, 1.2) * AD[b]).mean()
                    vf = 0.5 * ((v - RT[b]) ** 2).mean()
                    
                    # Safe KL calculation restricted to valid candidates
                    kl_mask = M[b]
                    kl_elem = ref_lp[b].exp() * (ref_lp[b] - lsm)
                    kl_elem = torch.where(kl_mask, kl_elem, torch.zeros_like(kl_elem))
                    kl = kl_elem.sum(-1).sum(-1).mean()
                    
                    # Safe entropy calculation restricted to valid candidates
                    p = lsm.exp()
                    ent_elem = -p * torch.where(kl_mask & (p > 1e-12), lsm, torch.zeros_like(lsm))
                    ent = ent_elem.sum(-1).mean()
                    
                    loss = pg + vf + beta_kl * kl - 0.003 * ent
                    opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(pol.parameters(), .5); opt.step()
            if (it + 1) % 10 == 0 or it == iters - 1:
                vs = val_score(pol, val_seeds)
                meanR = np.mean(Rs) if Rs else 0.0
                log(f"[PPO {it+1}] KL={kl.item():.3f} meanR={meanR:.3f} val rel.cost vs cadj = {vs*100:+.2f}%")
                if vs < best:
                    best, best_sd = vs, copy.deepcopy(pol.state_dict())
        pol.load_state_dict(best_sd)      # VAL-only checkpoint selection; the BC checkpoint is a candidate
        log(f"[PPO] selected checkpoint val rel.cost vs cadj = {best*100:+.2f}%")

    def shielded(pol, tau=0.05, stats=None):
        def ctrl(env, F, m):
            c = act(pol, F, m); b = h_cadj(F, m); Dh = env.Dh[0]     # estimate uses last measured demand only
            if evaluate(env.sc, env.t, c, Dh)[0] > (1 + tau) * evaluate(env.sc, env.t, b, Dh)[0]:
                if stats is not None: stats["fb"] += 1
                return b
            if stats is not None: stats["ok"] += 1
            return c
        return ctrl

    return Pol, act, dagger, ppo, shielded


def seed_iter(start):
    i = start
    while True:
        yield i; i += 1


def evaluate_all(name, seeds, size, ctrls, log=print):
    res = {k: [] for k in ctrls}; extra = {k: [] for k in ctrls}
    for s in seeds:
        sc = make_scenario(s, size)
        for k, c in ctrls.items():
            r = run(sc, c); res[k].append(r["J"]); extra[k].append((r["loss"], r["churn"]))
    log(f"\n=== {name} ({len(seeds)} paired scenarios) ===")
    for k in res:
        l, c = np.mean(extra[k], 0)
        log(f"{k:>14}: J={np.mean(res[k]):.3f}  loss={l*100:.2f}%  churn={c*100:.1f}%")
    for k in res:
        if k not in ("static", "cadj"): log(paired_report(res, "cadj", k))
    for k in res:
        if k != "static": log(paired_report(res, "static", k))
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tier", default="smoke"); a = ap.parse_args()
    cfg = {"smoke": dict(di=2, de=4, pi=4, pe=4, nv=6, nt=10),
           "dev": dict(di=4, de=30, pi=60, pe=16, nv=30, nt=100),
           "full": dict(di=5, de=60, pi=200, pe=16, nv=60, nt=200)}[a.tier]
    Pol, act, dagger, ppo, shielded = build_torch()
    import torch; torch.manual_seed(0)
    val = list(range(10000, 10000 + cfg["nv"]))
    print("tuned CADJ hysteresis on VAL:", tune_cadj(val))
    pol = Pol()
    dagger(pol, seed_iter(0), iters=cfg["di"], eps=cfg["de"])
    bc = copy.deepcopy(pol)
    ppo(pol, copy.deepcopy(bc), seed_iter(100000), val, iters=cfg["pi"], neps=cfg["pe"])
    stats = {"fb": 0, "ok": 0}
    ctrls = {"static": lambda e, F, m: h_static(F, m), "leastloaded": lambda e, F, m: h_leastloaded(F, m),
             "delay": lambda e, F, m: h_delay(F, m), "cadj": lambda e, F, m: h_cadj(F, m),
             "BC-only": lambda e, F, m: act(bc, F, m), "PPO-residual": lambda e, F, m: act(pol, F, m),
             "PPO+shield": shielded(pol, stats=stats), "teacher(priv)": teacher_ctrl}
    evaluate_all("TEST-ID", list(range(20000, 20000 + cfg["nt"])), None, ctrls)
    print(f"shield fallback rate = {stats['fb'] / max(1, stats['fb'] + stats['ok']) * 100:.1f}%")
    evaluate_all("TEST-SIZE (40 nodes, unseen)", list(range(40000, 40000 + max(10, cfg["nt"] // 4))), 40, ctrls)


if __name__ == "__main__":
    main()
