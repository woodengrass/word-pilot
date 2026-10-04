#!/usr/bin/env python3
"""Two follow-up simulations to docs/09 (results in docs/10).

1. Exam-oriented depth: when an exam date is set, the planner automatically
   lowers the per-word requirement (core sense + core usage, only the
   exam-frequent second senses, no spelling unless writing_required) and
   optionally lowers desired retention for in-scope targets. Compared with
   full depth on readiness at the exam date.

2. Self-assessment slider and personalization: a population of learners whose
   memory differs from the default FSRS weights by a time-scale factor m
   (m < 1 forgets faster). Schedulers either ignore m, use a noisy slider
   value, estimate m from answers (MAP over a grid, refit periodically), or
   combine slider prior + answers. Reports how close each gets to the 90%
   target retention and how fast the estimate converges.

Personalization here fits ONE parameter (a forgetting time-scale), standing in
for full 21-weight FSRS optimization. It shows the direction and speed of the
effect, not the exact gain of the real optimizer.

Usage: python3 tools/simulate_exam_personalization.py [--quick]
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_review_load import (  # noqa: E402
    AGAIN, FEEDBACK, FORM, GOOD, REMEDIATION_EXPLAIN, SENSE, USAGE, UnitKind,
    init_state, interval_days, retrievability, review,
)

HIGH_RISK_R = 0.80   # policy-v1 planner.high_risk_retrievability_threshold
EXAM_GUESS = 0.25    # 4-choice exam item


def cost(kind: UnitKind, failed: bool) -> float:
    base = kind.item_seconds + FEEDBACK
    return base + (base + REMEDIATION_EXPLAIN if failed else 0.0)


@dataclass
class Unit:
    kind: UnitKind
    word: int
    role: str                # core / usage / second_exam / second_other / form
    m_hat: float = 1.0       # scheduler's forgetting time-scale when last scheduled
    s: float = 0.0
    d: float = 0.0
    true_s: float = 0.0
    true_d: float = 0.0
    last_day: int = 0
    due_day: int = 0
    successes: int = 0
    delayed_successes: int = 0
    log: list = field(default_factory=list)   # (elapsed_days, observed_good) for fitting


class Learner:
    """Simulates one learner + one scheduler configuration day by day."""

    def __init__(self, rng: random.Random, true_m: float, budget_minutes: float,
                 desired_retention: float, new_before_reviews: bool = False,
                 guess_aware: bool = False, first_recall_p: float = 0.8):
        self.rng = rng
        self.true_m = true_m
        self.m_hat = 1.0
        self.budget = budget_minutes * 60
        self.retention = desired_retention
        self.first_recall_p = first_recall_p
        self.new_before_reviews = new_before_reviews
        self.guess_aware = guess_aware
        self.units: list[Unit] = []
        self.pending: list[tuple[int, UnitKind, int, str]] = []  # (eligible_day, kind, word, role)
        self.next_word = 0
        self.true_r_at_review: list[float] = []

    # scheduler view -------------------------------------------------------
    def sched_r(self, u: Unit, day: int) -> float:
        return retrievability((day - u.last_day) / u.m_hat, u.s)

    def schedule(self, u: Unit, day: int) -> None:
        u.m_hat = self.m_hat
        u.due_day = day + max(1, round(interval_days(u.s, self.retention) * self.m_hat))

    # learner view ---------------------------------------------------------
    def observe(self, u: Unit, true_recall: bool) -> int:
        if true_recall or self.rng.random() < u.kind.guess_rate:
            return GOOD
        return AGAIN

    def introduce(self, kind: UnitKind, word: int, role: str, day: int) -> float:
        u = Unit(kind, word, role)
        true_recall = self.rng.random() < self.first_recall_p
        rating = self.observe(u, true_recall)
        u.s, u.d = sched_init(rating == GOOD, kind.guess_rate if self.guess_aware else 0.0, self.first_recall_p)
        u.true_s, u.true_d = init_state(GOOD if true_recall else AGAIN)
        u.successes = int(rating == GOOD)
        u.last_day = day
        self.schedule(u, day)
        self.units.append(u)
        return kind.teach_seconds + cost(kind, rating == AGAIN)

    def do_review(self, u: Unit, day: int) -> float:
        elapsed = day - u.last_day
        true_r = retrievability(elapsed / self.true_m, u.true_s)
        self.true_r_at_review.append(true_r)
        true_recall = self.rng.random() < true_r
        rating = self.observe(u, true_recall)
        u.log.append((elapsed, rating == GOOD))
        u.s, u.d = sched_update(u.s, u.d, elapsed / u.m_hat, rating == GOOD,
                                u.kind.guess_rate if self.guess_aware else 0.0)
        u.true_s, u.true_d = review(u.true_s, u.true_d, elapsed / self.true_m, GOOD if true_recall else AGAIN)
        if rating == GOOD:
            u.successes += 1
            u.delayed_successes += 1
        u.last_day = day
        self.schedule(u, day)
        return cost(u.kind, rating == AGAIN)

    def true_r(self, u: Unit, day: int) -> float:
        return retrievability((day - u.last_day) / self.true_m, u.true_s)

    # one study day --------------------------------------------------------
    def study_day(self, day: int, new_word_units, words_available: int | None) -> None:
        """new_before_reviews=True is the docs/04 §8 exam ordering: high-risk due
        reviews, then new in-scope content, then the remaining due reviews.
        False: all due reviews first, then new content."""
        spent = 0.0
        due = [u for u in self.units if u.due_day <= day]
        due.sort(key=lambda u: self.sched_r(u, day))
        if self.new_before_reviews:
            high = [u for u in due if self.sched_r(u, day) < HIGH_RISK_R]
            rest = [u for u in due if self.sched_r(u, day) >= HIGH_RISK_R]
        else:
            high, rest = due, []
        for u in high:
            if spent >= self.budget:
                return
            spent += self.do_review(u, day)
        while spent < self.budget:
            idx = next((i for i, p in enumerate(self.pending) if p[0] <= day), None)
            if idx is not None:
                _, kind, word, role = self.pending.pop(idx)
                spent += self.introduce(kind, word, role, day)
                continue
            if words_available is not None and self.next_word >= words_available:
                break
            word = self.next_word
            self.next_word += 1
            units = new_word_units(self.rng)
            spent += self.introduce(units[0][0], word, units[0][1], day)
            for kind, role in units[1:]:
                self.pending.append((day + 1, kind, word, role))
        for u in rest:
            if spent >= self.budget:
                return
            spent += self.do_review(u, day)


def sched_init(good: bool, guess_rate: float, prior_recall: float) -> tuple[float, float]:
    """Initial FSRS state; a correct first click is blended with a guess like sched_update."""
    if not good or guess_rate == 0.0:
        return init_state(GOOD if good else AGAIN)
    q = prior_recall / (prior_recall + (1 - prior_recall) * guess_rate)
    (s_g, d_g), (s_a, d_a) = init_state(GOOD), init_state(AGAIN)
    return math.exp(q * math.log(s_g) + (1 - q) * math.log(s_a)), q * d_g + (1 - q) * d_a


def sched_update(s: float, d: float, elapsed: float, good: bool, guess_rate: float) -> tuple[float, float]:
    """FSRS update; with guess_rate > 0 a correct click is treated as recall with
    probability r / (r + (1 - r) * g) and the two outcomes' stabilities are blended
    geometrically (an arithmetic mean is dominated by the Good branch)."""
    if not good or guess_rate == 0.0:
        return review(s, d, elapsed, GOOD if good else AGAIN)
    r = retrievability(elapsed, s)
    q = r / (r + (1 - r) * guess_rate)
    s_good, d_good = review(s, d, elapsed, GOOD)
    s_again, d_again = review(s, d, elapsed, AGAIN)
    return math.exp(q * math.log(s_good) + (1 - q) * math.log(s_again)), q * d_good + (1 - q) * d_again


# ============================================================ experiment 1 ==
SECOND_SENSE_P = 0.6        # words with an important second sense
SECOND_EXAM_FREQ_P = 1 / 3  # share of those second senses that show up in exam data


def word_senses(rng: random.Random) -> tuple[bool, bool]:
    has_second = rng.random() < SECOND_SENSE_P
    return has_second, has_second and rng.random() < SECOND_EXAM_FREQ_P


def full_depth(rng):
    has2, exam2 = word_senses(rng)
    units = [(SENSE, "core"), (USAGE, "usage")]
    if has2:
        units.append((SENSE, "second_exam" if exam2 else "second_other"))
    units.append((FORM, "form"))
    return units


def exam_oriented(rng):
    _, exam2 = word_senses(rng)
    units = [(SENSE, "core"), (USAGE, "usage")]
    if exam2:
        units.append((SENSE, "second_exam"))
    return units


EXAM_ITEM_WEIGHT = {"core": 1.0, "usage": 0.5, "second_exam": 1.0}


@dataclass
class ExamCase:
    words: int
    days: int
    budget: float


def run_exam(case: ExamCase, strategy, retention: float, new_first: bool, seed: int) -> dict:
    rng = random.Random(seed)
    lr = Learner(rng, true_m=1.0, budget_minutes=case.budget, desired_retention=retention,
                 new_before_reviews=new_first)
    # Pre-draw each word's senses so every strategy faces the same exam.
    exam_words = [word_senses(random.Random(seed * 100_003 + w)) for w in range(case.words)]
    word_rngs = iter([random.Random(seed * 100_003 + w) for w in range(case.words)])
    for day in range(case.days):
        lr.study_day(day, lambda _r: strategy(next(word_rngs)), case.words)
    exam_day = case.days
    by_word: dict[int, dict[str, Unit]] = {}
    for u in lr.units:
        by_word.setdefault(u.word, {})[u.role] = u
    score_num = score_den = 0.0
    foundation_words = 0
    for w, (_, exam2) in enumerate(exam_words):
        roles = ["core", "usage"] + (["second_exam"] if exam2 else [])
        units = by_word.get(w, {})
        ok = True
        for role in roles:
            u = units.get(role)
            r = lr.true_r(u, exam_day) if u else 0.0
            score_num += EXAM_ITEM_WEIGHT[role] * (r + (1 - r) * EXAM_GUESS)
            score_den += EXAM_ITEM_WEIGHT[role]
            if not (u and u.successes >= 2 and u.delayed_successes >= 1):
                ok = False
        foundation_words += ok
    return {
        "started": len(by_word) / case.words,
        "foundation": foundation_words / case.words,
        "score": score_num / score_den,
    }


def experiment_exam(seeds) -> str:
    cases = [ExamCase(300, 30, 15), ExamCase(600, 60, 15), ExamCase(600, 30, 15),
             ExamCase(1200, 60, 15), ExamCase(1200, 60, 30)]
    strategies = [("完整深度 / 複習優先 / 0.90", full_depth, 0.90, False),
                  ("考試導向 / 複習優先 / 0.90", exam_oriented, 0.90, False),
                  ("考試導向 / 複習優先 / 0.85", exam_oriented, 0.85, False),
                  ("考試導向 / 計畫順序（新內容優先）", exam_oriented, 0.90, True)]
    lines = ["| 範圍 | 天數 | 每日分鐘 | 策略 | 考前已開始 | 考前達 Foundation | 預估範圍內答對率 |",
             "|---|---|---|---|---|---|---|"]
    for c in cases:
        for name, strat, ret, new_first in strategies:
            rs = [run_exam(c, strat, ret, new_first, s) for s in seeds]
            m = {k: statistics.fmean(r[k] for r in rs) for k in rs[0]}
            lines.append(f"| {c.words} 字 | {c.days} | {c.budget:g} | {name} | {m['started']:.0%} | "
                         f"{m['foundation']:.0%} | {m['score']:.0%} |")
    return "\n".join(lines)


# ============================================================ experiment 2 ==
M_GRID = [math.exp(x / 10) for x in range(-14, 12)]   # 0.25 .. 3.0
POP_SIGMA = 0.4      # spread of log(m) across learners
DAYS2 = 90


def log_likelihood(units: list[Unit], m: float, guess_aware: bool = True) -> float:
    """Replay each unit's observed answers under candidate m (scheduler model)."""
    ll = 0.0
    for u in units:
        if not u.log:
            continue
        s, d = sched_init(u.successes - u.delayed_successes > 0, u.kind.guess_rate if guess_aware else 0.0, 0.8)
        for elapsed, good in u.log:
            r = retrievability(elapsed / m, s)
            p = min(max(r + (1 - r) * u.kind.guess_rate, 1e-6), 1 - 1e-6)
            ll += math.log(p if good else 1 - p)
            s, d = sched_update(s, d, elapsed / m, good, u.kind.guess_rate if guess_aware else 0.0)
    return ll


def map_estimate(units: list[Unit], prior_mu: float, prior_sigma: float) -> float:
    best, best_lp = 1.0, -math.inf
    for m in M_GRID:
        lp = log_likelihood(units, m) - (math.log(m) - prior_mu) ** 2 / (2 * prior_sigma ** 2)
        if lp > best_lp:
            best, best_lp = m, lp
    return best


def core_profile(_rng):
    return [(SENSE, "core"), (USAGE, "usage")]


def run_learner(true_m: float, slider: float, slider_sigma: float, variant: str, seed: int) -> dict:
    rng = random.Random(seed)
    lr = Learner(rng, true_m=true_m, budget_minutes=15, desired_retention=0.90,
                 guess_aware=variant != "default_plain")
    # Posterior of log m given the slider reading (Gaussian prior x Gaussian measurement).
    w = POP_SIGMA ** 2 / (POP_SIGMA ** 2 + slider_sigma ** 2)
    slider_mu = w * math.log(slider)
    slider_sd = math.sqrt(POP_SIGMA ** 2 * slider_sigma ** 2 / (POP_SIGMA ** 2 + slider_sigma ** 2))
    if variant == "slider" or variant == "slider+data":
        lr.m_hat = math.exp(slider_mu)
    if variant == "oracle":
        lr.m_hat = true_m
    err_at = {}
    refit_days = {7, 14, 21, 28, 42, 56, 70, 84}
    for day in range(DAYS2):
        if variant in ("data", "slider+data") and day in refit_days:
            mu, sd = (slider_mu, slider_sd) if variant == "slider+data" else (0.0, POP_SIGMA)
            lr.m_hat = map_estimate(lr.units, mu, sd)
        lr.study_day(day, core_profile, None)
        if day + 1 in (14, 30, 90):
            err_at[day + 1] = abs(math.log(lr.m_hat / true_m))
    late = lr.true_r_at_review[len(lr.true_r_at_review) // 2:]
    return {
        "retention": statistics.fmean(late) if late else float("nan"),
        "words": lr.next_word,
        **{f"err{d}": v for d, v in err_at.items()},
    }


def experiment_personalization(n_learners: int) -> str:
    rng = random.Random(2026)
    learners = [math.exp(rng.gauss(0, POP_SIGMA)) for _ in range(n_learners)]
    variants = [("預設參數，未修正猜題（目前計畫）", "default_plain"),
                ("預設參數＋猜題修正", "default"), ("只用滑桿", "slider"),
                ("從作答資料學", "data"), ("滑桿＋作答資料", "slider+data"),
                ("理想上限（完全知道）", "oracle")]
    out = []
    for slider_sigma, title in ((0.2, "滑桿自評準確（誤差小）"), (0.6, "滑桿自評不準（誤差大）")):
        noise = random.Random(int(slider_sigma * 1000))
        sliders = [m * math.exp(noise.gauss(0, slider_sigma)) for m in learners]
        lines = [f"#### {title}", "",
                 "| 排程方式 | 後半段實際記憶率（目標 90%） | 忘得快的人 | 記得牢的人 | 90 天開始字數 | 估計誤差 d14 | d30 | d90 |",
                 "|---|---|---|---|---|---|---|---|"]
        for name, v in variants:
            if slider_sigma == 0.6 and v in ("default_plain", "default", "data", "oracle"):
                continue  # identical to the first table; slider accuracy does not affect them
            rs = [run_learner(m, sl, slider_sigma, v, 10 + i) for i, (m, sl) in enumerate(zip(learners, sliders))]
            weak = [r["retention"] for r, m in zip(rs, learners) if m < 0.75]
            strong = [r["retention"] for r, m in zip(rs, learners) if m > 1.35]

            def errs(d):
                return statistics.fmean(math.exp(r[f"err{d}"]) - 1 for r in rs)
            lines.append(
                f"| {name} | {statistics.fmean(r['retention'] for r in rs):.1%} | "
                f"{statistics.fmean(weak):.1%} | {statistics.fmean(strong):.1%} | "
                f"{statistics.fmean(r['words'] for r in rs):.0f} | "
                f"{errs(14):.0%} | {errs(30):.0%} | {errs(90):.0%} |")
        out.append("\n".join(lines))
    n_weak = sum(m < 0.75 for m in learners)
    n_strong = sum(m > 1.35 for m in learners)
    out.append(f"（{n_learners} 位模擬學生；忘得快 m<0.75 共 {n_weak} 位，記得牢 m>1.35 共 {n_strong} 位）")
    return "\n\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer seeds/learners for a fast smoke run")
    args = ap.parse_args()
    seeds = (1,) if args.quick else (1, 2, 3)
    print("## 實驗一：考試導向背法\n")
    print(experiment_exam(seeds) + "\n")
    print("## 實驗二：滑桿自評與個人化（core 深度 / 15 分 / 90 天）\n")
    print(experiment_personalization(12 if args.quick else 40))


if __name__ == "__main__":
    main()
