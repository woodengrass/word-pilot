#!/usr/bin/env python3
"""Continuous FSRS personalization with and without overfitting safeguards (docs/12).

Ground truth is intentionally richer than the scheduler's model:
- Each learner has their own FSRS-6 weights (initial stability, recall growth,
  lapse stability, forgetting-curve decay all vary), and the population mean
  differs from the Anki default weights the scheduler starts with.
- Each word unit has its own hidden difficulty (stability multiplier, initial
  difficulty offset) that the scheduler never sees directly.
- Learners change over time: stable, gradually improving, or suddenly worse
  mid-way (e.g. a busy semester).
- Answers are noisy: 4-choice guessing on recognition items, ~3% slips, typed
  items without guessing. Daily time, answer speed and attendance vary.

Schedulers are plain FSRS-6 (no guess correction). Personalization fits 8 of
the 21 weights by maximum likelihood (L-BFGS-B) on the learner's own answers
and replays every unit's history when the weights change, like Anki does.

Variants:
  fixed      default weights forever
  once       fit once after 1,000 reviews, then frozen
  naive      refit every 250 reviews on all data, no safeguards
  guarded    refit every 250 reviews with safeguards: L2 pull toward a prior,
             recency weighting, held-out acceptance test, damped steps
  guarded+   same, but the prior is the population mean (as if learned in beta)
  guarded-   weaker safeguards: L2 10 instead of 30, step 0.6 instead of 0.3
  balanced   population prior + weaker safeguards + 60-day recency half-life
  oracle     true learner weights and true drift (still blind to word difficulty)

Requires numpy and scipy. Usage:
  python3 tools/simulate_continuous_personalization.py [--quick] [--workers N]
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

DEFAULT_W = np.array([0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
                      1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542])
FIT_IDX = np.array([0, 2, 8, 9, 10, 11, 14, 20])
LOWER = np.array([0.01, 0.01, 0.01, 0.001, 0.01, 0.01, 0.01, 0.1])
UPPER = np.array([50.0, 100.0, 4.5, 0.8, 3.5, 5.0, 6.0, 0.8])
RETENTION = 0.90
DAYS = 180
GUESS = 0.25
ADHERENCE = 0.85   # share of days the learner studies
ITEM_K_SD = 0.35   # spread of hidden word difficulty (log stability multiplier)
ITEM_D_SD = 1.5    # spread of hidden initial-difficulty offset
SLIP = 0.03
EPS = 1e-6


# ------------------------------------------------------------- FSRS core ----
def factor(w20):
    return 0.9 ** (-1.0 / w20) - 1.0


def retr(elapsed, s, w20):
    return (1.0 + factor(w20) * elapsed / s) ** (-w20)


def d0(w, g):
    return np.clip(w[4] - np.exp(w[5] * (g - 1)) + 1.0, 1.0, 10.0)


def step(w, s, d, r, good):
    s_recall = s * (1.0 + math.e ** w[8] * (11.0 - d) * s ** (-w[9]) * (np.exp((1.0 - r) * w[10]) - 1.0))
    s_forget = np.minimum(w[11] * d ** (-w[12]) * ((s + 1.0) ** w[13] - 1.0) * np.exp((1.0 - r) * w[14]),
                          s / math.exp(w[17] * w[18]))
    g = np.where(good, 3.0, 1.0)
    d_new = np.clip(w[7] * d0(w, 4.0) + (1 - w[7]) * (d + (10.0 - d) * (-w[6] * (g - 3.0)) / 9.0), 1.0, 10.0)
    return np.maximum(np.where(good, s_recall, s_forget), 0.001), d_new


def step_short(w, s, d, good):
    """FSRS-6 same-day (short-term) update, used for remediation right after a miss."""
    g = np.where(good, 3.0, 1.0)
    inc = np.exp(w[17] * (g - 3.0 + w[18])) * s ** (-w[19])
    inc = np.where(good, np.maximum(inc, 1.0), inc)
    d_new = np.clip(w[7] * d0(w, 4.0) + (1 - w[7]) * (d + (10.0 - d) * (-w[6] * (g - 3.0)) / 9.0), 1.0, 10.0)
    return np.maximum(s * inc, 0.001), d_new


def interval(s, w20):
    return max(1, round(float(s) / factor(w20) * (RETENTION ** (-1.0 / w20) - 1.0)))


# --------------------------------------------------------- vector replay ----
@dataclass
class History:
    elapsed: np.ndarray   # [N, T] days since previous event (col 0 = introduction)
    good: np.ndarray      # [N, T] bool
    mask: np.ndarray      # [N, T] bool
    day: np.ndarray       # [N, T] event day
    length: np.ndarray    # [N]


def build_history(units) -> History:
    n = len(units)
    t = max(len(u.log_day) for u in units)
    el = np.zeros((n, t)); gd = np.zeros((n, t), bool); mk = np.zeros((n, t), bool); dy = np.zeros((n, t))
    for i, u in enumerate(units):
        k = len(u.log_day)
        days = np.array(u.log_day, float)
        dy[i, :k] = days
        el[i, 1:k] = np.diff(days)
        gd[i, :k] = u.log_good
        mk[i, :k] = True
    return History(el, gd, mk, dy, mk.sum(1))


def replay(w, h: History):
    """Returns per-event predicted recall (cols >= 1) and final (S, D) per unit."""
    s = np.where(h.good[:, 0], w[2], w[0]).astype(float)
    d = d0(w, np.where(h.good[:, 0], 3.0, 1.0))
    pred = np.full(h.good.shape, np.nan)
    for t in range(1, h.good.shape[1]):
        m = h.mask[:, t]
        if not m.any():
            break
        same_day = h.elapsed[:, t] <= 0
        r = retr(np.maximum(h.elapsed[:, t], 0.0), s, w[20])
        pred[:, t] = np.where(same_day, np.nan, r)   # same-day remediation is not a memory test
        s_long, d_long = step(w, s, d, r, h.good[:, t])
        s_short, d_short = step_short(w, s, d, h.good[:, t])
        s2 = np.where(same_day, s_short, s_long); d2 = np.where(same_day, d_short, d_long)
        s = np.where(m, s2, s); d = np.where(m, d2, d)
    return pred, s, d


def nll(pred, h: History, sel, weight):
    p = np.clip(pred[sel], EPS, 1 - EPS)
    y = h.good[sel]
    return -np.sum(weight[sel] * (y * np.log(p) + (1 - y) * np.log(1 - p)))


def full_w(theta):
    w = DEFAULT_W.copy(); w[FIT_IDX] = theta
    return w


def fit(h: History, start, prior, today, *, l2, half_life, cutoff_day):
    weight = np.ones_like(h.elapsed) if half_life is None else 0.5 ** ((today - h.day) / half_life)
    sel = h.mask & (h.elapsed > 0)
    if cutoff_day is not None:
        sel &= h.day < cutoff_day
    log_prior = np.log(prior)

    def obj(theta):
        pred, _, _ = replay(full_w(theta), h)
        loss = nll(pred, h, sel, weight)
        if l2:
            loss += l2 * np.sum((np.log(np.maximum(theta, 1e-6)) - log_prior) ** 2)
        return loss
    res = minimize(obj, np.clip(start, LOWER, UPPER), method="L-BFGS-B",
                   bounds=list(zip(LOWER, UPPER)), options={"maxiter": 60})
    return res.x


def heldout_nll(theta, h: History, cutoff_day):
    pred, _, _ = replay(full_w(theta), h)
    sel = h.mask & (h.elapsed > 0) & (h.day >= cutoff_day)
    n = sel.sum()
    return nll(pred, h, sel, np.ones_like(h.elapsed)) / max(n, 1), n


# ------------------------------------------------------------ simulation ----
@dataclass
class Kind:
    name: str
    item_s: float
    teach_s: float
    guess: float


SENSE = Kind("sense", 12, 15, GUESS)
USAGE = Kind("usage", 10, 15, GUESS)
FORM = Kind("form", 20, 0, 0.0)
FEEDBACK = 5.0


@dataclass
class Unit:
    kind: Kind
    k: float              # hidden word difficulty: true stability multiplier
    d_off: float          # hidden initial-difficulty offset
    s: float = 0.0
    d: float = 0.0
    ts: float = 0.0
    td: float = 0.0
    last: int = 0
    due: int = 0
    log_day: list = field(default_factory=list)
    log_good: list = field(default_factory=list)


@dataclass
class Scenario:
    name: str
    drift: str = "stable"         # stable / improving / worse_mid
    minutes: float = 15.0


def drift_m(kind: str, day: int) -> float:
    if kind == "improving":
        return 1.0 + 0.5 * day / DAYS
    if kind == "worse_mid":
        return 0.6 if day >= 90 else 1.0
    return 1.0


POP_MEAN = DEFAULT_W.copy()
POP_MEAN[[0, 1, 2, 3]] *= 0.6     # students start weaker than Anki users
POP_MEAN[8] -= 0.25
POP_MEAN[11] *= 0.8
POP_MEAN[20] *= 1.6               # steeper forgetting curve


def draw_learner(rng: random.Random) -> np.ndarray:
    w = POP_MEAN.copy()
    a = math.exp(rng.gauss(0, 0.5))
    w[[0, 1, 2, 3]] *= a
    w[8] += rng.gauss(0, 0.3)
    w[10] = max(0.05, w[10] + rng.gauss(0, 0.2))
    w[11] *= math.exp(rng.gauss(0, 0.4))
    w[20] = min(0.75, w[20] * math.exp(rng.gauss(0, 0.3)))
    return w


VARIANTS = ["fixed", "once", "naive", "guarded-", "guarded", "guarded+", "balanced", "oracle"]
GUARD = {"guarded": (30.0, 0.3, 120.0), "guarded+": (30.0, 0.3, 120.0), "guarded-": (10.0, 0.6, 120.0),
         "balanced": (10.0, 0.6, 60.0)}  # (L2, step, recency half-life days)
POP_PRIOR = ("guarded+", "balanced")


def run(scn: Scenario, variant: str, learner_seed: int) -> dict:
    lrng = random.Random(learner_seed)
    true_w = draw_learner(lrng)
    speed = math.exp(lrng.gauss(0, 0.25))
    rng = random.Random(learner_seed * 7 + 1)  # same answer stream seed for all variants
    world = random.Random(learner_seed * 13 + 5)
    prior = POP_MEAN[FIT_IDX] if variant in POP_PRIOR else DEFAULT_W[FIT_IDX]
    theta = prior.copy()
    w = full_w(theta)
    if variant == "oracle":
        w = true_w.copy()
    units: list[Unit] = []
    pending: list[tuple[int, Kind]] = []
    since_fit, fitted_once, n_reviews = 0, False, 0
    records = []        # (day, predicted, observed, true_r)
    volatility = []     # mean |log interval change| per accepted update
    updates = 0

    def oracle_m(day):
        return drift_m(scn.drift, day) if variant == "oracle" else 1.0

    def answer(u: Unit, true_r: float) -> tuple[bool, bool]:
        recalled = rng.random() < true_r
        if recalled:
            obs = rng.random() >= SLIP
        else:
            obs = rng.random() < u.kind.guess
        return recalled, obs

    def remediate(u: Unit, day: int) -> None:
        """Plan docs/04 §8: after a miss, re-teach and retry the same day (up to 3 times)."""
        for _ in range(3):
            recalled, obs = answer(u, 0.9)
            ts, td = step_short(true_w, np.array(u.ts), np.array(u.td), np.array(recalled))
            u.ts, u.td = float(ts), float(td)
            s, d = step_short(w, np.array(u.s), np.array(u.d), np.array(obs))
            u.s, u.d = float(s), float(d)
            u.log_day.append(day); u.log_good.append(obs)
            if obs:
                break
        u.due = day + round(interval(u.s, w[20]) * oracle_m(day))

    def introduce(kind: Kind, day: int) -> float:
        u = Unit(kind, k=math.exp(world.gauss(0, ITEM_K_SD)), d_off=world.gauss(0, ITEM_D_SD))
        recalled, obs = answer(u, 0.8)
        u.ts = true_w[2] if recalled else true_w[0]
        u.td = float(np.clip(d0(true_w, 3.0 if recalled else 1.0) + u.d_off, 1, 10))
        u.s = float(w[2] if obs else w[0]); u.d = float(d0(w, 3.0 if obs else 1.0))
        u.last = day
        u.due = day + round(interval(u.s, w[20]) * oracle_m(day))
        u.log_day.append(day); u.log_good.append(obs)
        units.append(u)
        if not obs:
            remediate(u, day)
        return speed * (kind.teach_s + kind.item_s + FEEDBACK + (0 if obs else kind.item_s + FEEDBACK + 10))

    def review(u: Unit, day: int) -> float:
        el = day - u.last
        m_true = drift_m(scn.drift, day)
        true_r = float(retr(el / (m_true * u.k), u.ts, true_w[20]))
        pred = float(retr(el / oracle_m(day), u.s, w[20]))
        recalled, obs = answer(u, true_r)
        records.append((day, pred, obs, true_r, el))
        ts, td = step(true_w, np.array(u.ts), np.array(u.td), np.array(true_r), np.array(recalled))
        u.ts, u.td = float(ts), float(td)
        s, d = step(w, np.array(u.s), np.array(u.d), np.array(pred), np.array(obs))
        u.s, u.d = float(s), float(d)
        u.last = day
        u.due = day + round(interval(u.s, w[20]) * oracle_m(day))
        u.log_day.append(day); u.log_good.append(obs)
        if not obs:
            remediate(u, day)
        return speed * (u.kind.item_s + FEEDBACK + (0 if obs else u.kind.item_s + FEEDBACK + 10))

    def apply_weights(new_w, day):
        nonlocal w
        h = build_history(units)
        before = np.array([interval(u.s, w[20]) for u in units], float)
        _, s, d = replay(new_w, h)
        w = new_w
        after = []
        for u, si, di in zip(units, s, d):
            u.s, u.d = float(si), float(di)
            u.due = u.last + interval(u.s, w[20])
            after.append(interval(u.s, w[20]))
        volatility.append(float(np.mean(np.abs(np.log(np.array(after) / before)))))

    for day in range(DAYS):
        # --- personalization -------------------------------------------------
        if variant != "fixed" and variant != "oracle" and n_reviews >= 400 and units:
            due_fit = (variant == "once" and not fitted_once and n_reviews >= 1000) or \
                      (variant != "once" and since_fit >= 250)
            if due_fit:
                h = build_history(units)
                cur = w[FIT_IDX]
                if variant in ("once", "naive"):
                    new = fit(h, cur, prior, day, l2=0.0, half_life=None, cutoff_day=None)
                    apply_weights(full_w(new), day); updates += 1
                else:
                    cutoff = day - 21
                    l2, step_frac, half_life = GUARD[variant]
                    cand = fit(h, cur, prior, day, l2=l2, half_life=half_life, cutoff_day=cutoff)
                    nll_new, n_hold = heldout_nll(cand, h, cutoff)
                    nll_cur, _ = heldout_nll(cur, h, cutoff)
                    if n_hold >= 100 and nll_new < nll_cur * 0.995:
                        damped = np.exp(np.log(cur) + step_frac * (np.log(cand) - np.log(cur)))
                        apply_weights(full_w(damped), day); updates += 1
                fitted_once = True
                since_fit = 0
        # --- study day --------------------------------------------------------
        if rng.random() >= ADHERENCE:
            continue
        budget = scn.minutes * 60 * rng.uniform(0.6, 1.4)
        spent = 0.0
        due = sorted((u for u in units if u.due <= day),
                     key=lambda u: retr((day - u.last) / oracle_m(day), u.s, w[20]))
        for u in due:
            if spent >= budget:
                break
            spent += review(u, day); n_reviews += 1; since_fit += 1
        while spent < budget:
            idx = next((i for i, (e, _) in enumerate(pending) if e <= day), None)
            if idx is not None:
                spent += introduce(pending.pop(idx)[1], day)
                continue
            spent += introduce(SENSE, day)
            pending.append((day + 1, USAGE))
            if world.random() < 0.3:
                pending.append((day + 1, FORM))

    m_end = drift_m(scn.drift, DAYS)
    remembered = sum(float(retr((DAYS - u.last) / (m_end * u.k), u.ts, true_w[20])) for u in units)
    out = {"units": len(units), "reviews": n_reviews, "updates": updates, "remembered": remembered,
           "volatility": statistics.fmean(volatility) if volatility else 0.0,
           "max_volatility": max(volatility) if volatility else 0.0}
    for lo, hi in ((0, 60), (60, 120), (120, 180)):
        rs = [r for r in records if lo <= r[0] < hi]
        if not rs:
            continue
        p = np.clip(np.array([r[1] for r in rs]), EPS, 1 - EPS)
        y = np.array([r[2] for r in rs], float)
        out[f"logloss_{hi}"] = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
        out[f"bias_{hi}"] = float(np.mean(p) - np.mean(y))
        bins = np.minimum((p * 10).astype(int), 9)
        out[f"ece_{hi}"] = float(sum(abs(p[bins == b].mean() - y[bins == b].mean()) * (bins == b).sum()
                                     for b in range(10) if (bins == b).any()) / len(p))
        out[f"true_{hi}"] = float(np.mean([r[3] for r in rs]))
        mature = [r[3] for r in rs if r[4] >= 3]
        if mature:
            out[f"mature_{hi}"] = float(np.mean(mature))
    return out


SCENARIOS = [Scenario("記憶穩定"), Scenario("逐漸進步（半年後 ×1.5）", drift="improving"),
             Scenario("第 90 天起突然變差（×0.6）", drift="worse_mid"),
             Scenario("使用量少（每天 6 分）", minutes=6.0)]
LABEL = {"fixed": "固定預設參數", "once": "1,000 題後算一次就固定", "naive": "每 250 題完全重算（無保護）",
         "guarded-": "持續更新＋較弱保護（先驗＝Anki 預設）",
         "guarded": "持續更新＋保護（先驗＝Anki 預設）", "guarded+": "持續更新＋保護（先驗＝beta 族群值）",
         "balanced": "建議組合：beta 族群值＋較弱保護＋近 60 天加權",
         "oracle": "理想上限（知道真實參數）"}


def _job(args):
    scn, variant, seed = args
    return scn.name, variant, run(scn, variant, seed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="run only these variants")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--learners", type=int, default=24)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    n = 4 if args.quick else args.learners
    variants = args.only or VARIANTS
    jobs = [(s, v, 1000 + i) for s in SCENARIOS for v in variants for i in range(n)]
    results: dict = {}
    with ProcessPoolExecutor(args.workers) as ex:
        for name, v, r in ex.map(_job, jobs, chunksize=1):
            results.setdefault((name, v), []).append(r)
    for scn in SCENARIOS:
        print(f"### {scn.name}（{n} 位學生，{DAYS} 天）\n")
        print("| 排程方式 | 校準誤差 0–60 天 | 60–120 | 120–180 | 穩定字記憶率 0–60 | 60–120 | 120–180 | 全部複習記憶率 120–180 | 參數更新次數 | 每次更新排程平均變動 | 最大一次變動 | 開始學的單元 | 第 180 天實際記得的單元 |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for v in variants:
            rs = results[(scn.name, v)]

            def m(k):
                vals = [r[k] for r in rs if k in r]
                return statistics.fmean(vals) if vals else float("nan")
            vol = lambda k: math.exp(m(k)) - 1  # mean |log ratio| -> typical % change
            print(f"| {LABEL[v]} | {m('ece_60'):.1%} | {m('ece_120'):.1%} | {m('ece_180'):.1%} | "
                  f"{m('mature_60'):.1%} | {m('mature_120'):.1%} | {m('mature_180'):.1%} | {m('true_180'):.1%} | "
                  f"{m('updates'):.1f} | {vol('volatility'):.0%} | {vol('max_volatility'):.0%} | "
                  f"{m('units'):.0f} | {m('remembered'):.0f} |")
        print()


if __name__ == "__main__":
    main()
