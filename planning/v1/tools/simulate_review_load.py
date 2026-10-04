#!/usr/bin/env python3
"""Review-load simulation for the V1 plan.

Question: with a fixed daily time budget, how much of it goes to reviews as
words accumulate, and how many new words can still be admitted, depending on
how many MemoryUnits (target x response_mode) each word expands into?

Model (deliberately simple, all assumptions listed in docs/09):
- Each word expands into units per a "profile". The core-sense unit is
  introduced first; the word's other units become eligible the next day.
- Each day: due reviews first (lowest scheduler retrievability first), then
  new units with whatever time is left. Unfinished reviews carry over.
- Two FSRS-6 states per unit: "scheduler" (updated with the observed answer,
  which includes 4-choice guessing on recognition items) and "true" (updated
  with whether the learner actually recalled). Default FSRS-6 weights.
- Costs come from contracts/policy-v1.json seed_seconds.

Pure standard library. `--check-fsrs` compares the FSRS functions against
py-fsrs (pip install fsrs) if it is installed.

Usage:
  python3 tools/simulate_review_load.py                 # print report tables
  python3 tools/simulate_review_load.py --csv out.csv   # also dump daily series
  python3 tools/simulate_review_load.py --check-fsrs
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = json.loads((ROOT / "contracts/policy-v1.json").read_text(encoding="utf-8"))
SEED_SECONDS = POLICY["cost"]["seed_seconds"]

# ---------------------------------------------------------------- FSRS-6 ----
# Default FSRS-6 weights (identical to py-fsrs 6.x Scheduler defaults).
W = (0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722, 0.1666, 0.796,
     1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425, 0.0912, 0.0658, 0.1542)
DECAY = -W[20]
FACTOR = 0.9 ** (1 / DECAY) - 1
AGAIN, GOOD = 1, 3


def retrievability(elapsed_days: float, s: float) -> float:
    return (1 + FACTOR * elapsed_days / s) ** DECAY


def init_state(rating: int) -> tuple[float, float]:
    s = max(W[rating - 1], 0.001)
    d = min(max(W[4] - math.exp(W[5] * (rating - 1)) + 1, 1.0), 10.0)
    return s, d


def next_difficulty(d: float, rating: int) -> float:
    d_easy = W[4] - math.exp(W[5] * 3) + 1
    damped = d + (10.0 - d) * (-W[6] * (rating - 3)) / 9.0
    return min(max(W[7] * d_easy + (1 - W[7]) * damped, 1.0), 10.0)


def next_stability(s: float, d: float, r: float, rating: int) -> float:
    if rating == AGAIN:
        long_term = W[11] * d ** -W[12] * ((s + 1) ** W[13] - 1) * math.exp((1 - r) * W[14])
        new_s = min(long_term, s / math.exp(W[17] * W[18]))
    else:
        new_s = s * (1 + math.exp(W[8]) * (11 - d) * s ** -W[9] * (math.exp((1 - r) * W[10]) - 1))
    return max(new_s, 0.001)


def review(s: float, d: float, elapsed_days: float, rating: int) -> tuple[float, float]:
    r = retrievability(elapsed_days, s)
    return next_stability(s, d, r, rating), next_difficulty(d, rating)


def interval_days(s: float, desired_retention: float) -> int:
    return max(1, round(s / FACTOR * (desired_retention ** (1 / DECAY) - 1)))


# ------------------------------------------------------------- scenario ----
@dataclass(frozen=True)
class UnitKind:
    name: str
    item_seconds: float      # question time (feedback added separately)
    teach_seconds: float     # one-off short teaching before first answer
    guess_rate: float        # chance of a correct click without recall


SENSE = UnitKind("sense_recognition", SEED_SECONDS["sentence_choice"], SEED_SECONDS["teaching"], 0.25)
USAGE = UnitKind("usage_slot", SEED_SECONDS["slot_choice"], SEED_SECONDS["teaching"], 0.25)
FORM = UnitKind("form_cued_recall", SEED_SECONDS["typed_recall"], 0.0, 0.0)
EXACT = UnitKind("exact_form", SEED_SECONDS["typed_recall"], 0.0, 0.0)

# Profiles: list of (kind, probability the word has this unit). First entry is the core sense.
PROFILES: dict[str, list[tuple[UnitKind, float]]] = {
    "minimal": [(SENSE, 1.0)],
    "core": [(SENSE, 1.0), (USAGE, 1.0)],
    "standard": [(SENSE, 1.0), (SENSE, 0.6), (USAGE, 1.0), (FORM, 1.0)],
    "writing": [(SENSE, 1.0), (SENSE, 0.6), (USAGE, 1.0), (FORM, 1.0), (EXACT, 1.0)],
}


@dataclass
class Scenario:
    label: str
    profile: str = "standard"
    budget_minutes: float = 15
    days: int = 180
    desired_retention: float = POLICY["memory"]["desired_retention"]
    guessing: bool = True
    adherence: float = 1.0            # probability of studying on a given day
    first_recall_p: float = 0.8       # true recall on the first answer right after teaching
    cost_scale: float = 1.0           # multiplies every seed cost (learner slower/faster than prior)
    true_memory_scale: float = 1.0    # true stability relative to what default FSRS weights assume
    seeds: tuple[int, ...] = (1, 2, 3)


@dataclass
class Unit:
    kind: UnitKind
    word: int
    s: float = 0.0
    d: float = 0.0
    true_s: float = 0.0
    true_d: float = 0.0
    last_day: int = 0
    due_day: int = 0


@dataclass
class DayStats:
    day: int
    studied: bool
    review_seconds: float = 0.0
    new_seconds: float = 0.0
    reviews: int = 0
    new_units: int = 0
    new_words: int = 0
    overdue_left: int = 0
    guessed_goods: int = 0
    goods: int = 0


@dataclass
class RunResult:
    daily: list[DayStats]
    words_started: list[int] = field(default_factory=list)   # cumulative by day
    words_complete: list[int] = field(default_factory=list)
    true_retention_end: float = 0.0
    units_end: int = 0


FEEDBACK = SEED_SECONDS["feedback"]
REMEDIATION_EXPLAIN = 10.0  # extra explanation after a miss (engineering guess)


def answer_cost(kind: UnitKind, failed: bool, scale: float) -> float:
    base = kind.item_seconds + FEEDBACK
    # A miss costs one short-term remediation attempt plus a short explanation.
    return scale * (base + (base + REMEDIATION_EXPLAIN if failed else 0.0))


def run(sc: Scenario, seed: int) -> RunResult:
    rng = random.Random(seed)
    budget = sc.budget_minutes * 60
    units: list[Unit] = []
    pending_followups: list[tuple[int, UnitKind]] = []   # (eligible_day, kind) for started words
    followup_word: list[int] = []
    word_units_total: dict[int, int] = {}
    word_units_started: dict[int, int] = {}
    next_word = 0
    result = RunResult(daily=[])

    def observe(u: Unit, true_recall: bool) -> int:
        if true_recall:
            return GOOD
        if sc.guessing and rng.random() < u.kind.guess_rate:
            return GOOD
        return AGAIN

    def introduce(kind: UnitKind, word: int, day: int, stats: DayStats) -> float:
        true_recall = rng.random() < sc.first_recall_p
        rating = observe(Unit(kind, word), true_recall)
        u = Unit(kind, word)
        u.s, u.d = init_state(rating)
        u.true_s, u.true_d = init_state(GOOD if true_recall else AGAIN)
        u.last_day = day
        u.due_day = day + interval_days(u.s, sc.desired_retention)
        units.append(u)
        word_units_started[word] = word_units_started.get(word, 0) + 1
        stats.new_units += 1
        return sc.cost_scale * kind.teach_seconds + answer_cost(kind, rating == AGAIN, sc.cost_scale)

    for day in range(sc.days):
        studied = rng.random() < sc.adherence
        stats = DayStats(day=day, studied=studied)
        if studied:
            spent = 0.0
            due = [u for u in units if u.due_day <= day]
            due.sort(key=lambda u: retrievability(day - u.last_day, u.s))
            for u in due:
                if spent >= budget:
                    break
                elapsed = day - u.last_day
                true_recall = rng.random() < retrievability(elapsed, u.true_s * sc.true_memory_scale)
                rating = observe(u, true_recall)
                stats.goods += rating == GOOD
                stats.guessed_goods += rating == GOOD and not true_recall
                u.s, u.d = review(u.s, u.d, elapsed, rating)
                u.true_s, u.true_d = review(u.true_s, u.true_d, elapsed, GOOD if true_recall else AGAIN)
                u.last_day = day
                u.due_day = day + interval_days(u.s, sc.desired_retention)
                cost = answer_cost(u.kind, rating == AGAIN, sc.cost_scale)
                spent += cost
                stats.review_seconds += cost
                stats.reviews += 1
            # New content: finish started words first, then start new words.
            while spent < budget:
                idx = next((i for i, (eligible, _) in enumerate(pending_followups) if eligible <= day), None)
                if idx is not None:
                    _, kind = pending_followups.pop(idx)
                    word = followup_word.pop(idx)
                    cost = introduce(kind, word, day, stats)
                else:
                    word = next_word
                    next_word += 1
                    kinds = [k for i, (k, p) in enumerate(PROFILES[sc.profile]) if i == 0 or rng.random() < p]
                    word_units_total[word] = len(kinds)
                    cost = introduce(kinds[0], word, day, stats)
                    for k in kinds[1:]:
                        pending_followups.append((day + 1, k))
                        followup_word.append(word)
                    stats.new_words += 1
                spent += cost
                stats.new_seconds += cost
        stats.overdue_left = sum(1 for u in units if u.due_day <= day and u.last_day != day)
        result.daily.append(stats)
        result.words_started.append(len(word_units_total))
        result.words_complete.append(sum(1 for w, n in word_units_total.items() if word_units_started.get(w, 0) == n))

    end = sc.days
    if units:
        result.true_retention_end = statistics.fmean(
            retrievability(end - u.last_day, u.true_s * sc.true_memory_scale) for u in units)
    result.units_end = len(units)
    return result


# --------------------------------------------------------------- report ----
def window_mean(values: list[float], end_day: int, width: int = 7) -> float:
    chunk = values[max(0, end_day - width):end_day]
    return statistics.fmean(chunk) if chunk else 0.0


def summarize(sc: Scenario) -> dict:
    runs = [run(sc, s) for s in sc.seeds]
    budget = sc.budget_minutes * 60
    checkpoints = [d for d in (30, 90, 180, 365) if d <= sc.days]

    def avg(fn):
        return statistics.fmean(fn(r) for r in runs)

    out = {"label": sc.label, "scenario": sc}
    for d in checkpoints:
        out[f"words_d{d}"] = avg(lambda r: r.words_started[d - 1])
        out[f"complete_d{d}"] = avg(lambda r: r.words_complete[d - 1])
        out[f"review_share_d{d}"] = avg(
            lambda r: window_mean([x.review_seconds / budget for x in r.daily if x.studied],
                                  sum(1 for x in r.daily[:d] if x.studied)))
    last = sc.days
    out["new_words_per_day_tail"] = avg(lambda r: window_mean([x.new_words for x in r.daily], last, 30))
    out["overdue_end"] = avg(lambda r: r.daily[-1].overdue_left)
    out["true_retention_end"] = avg(lambda r: r.true_retention_end)
    out["guess_share"] = avg(lambda r: sum(x.guessed_goods for x in r.daily) / max(1, sum(x.goods for x in r.daily)))
    out["units_per_word"] = avg(lambda r: r.units_end / max(1, r.words_started[-1]))
    out["runs"] = runs
    return out


def scenarios() -> list[list[Scenario]]:
    grid = [Scenario(f"{p} / {b} 分", profile=p, budget_minutes=b)
            for p in PROFILES for b in (10, 15, 30)]
    sens = [
        Scenario("standard / 15 分（基準）"),
        Scenario("不計猜測（純回想）", guessing=False),
        Scenario("desired_retention 0.85", desired_retention=0.85),
        Scenario("desired_retention 0.95", desired_retention=0.95),
        Scenario("每週約缺 2 天（adherence 0.7）", adherence=0.7),
        Scenario("耗時比先驗慢 1.5 倍", cost_scale=1.5),
        Scenario("真實記憶比預設參數弱 40%", true_memory_scale=0.6),
    ]
    long = [Scenario(f"{p} / 15 分 / 365 天", profile=p, days=365) for p in ("minimal", "standard")]
    return [grid, sens, long]


def fmt_table(rows: list[dict], days: int) -> str:
    cps = [d for d in (30, 90, 180, 365) if d <= days]
    head = ["情境", "units/字"] + [f"已開始字數 d{d}" for d in cps] + [f"複習占比 d{d}" for d in cps] + \
           ["末30天 新字/日", "末日積欠 units", "真實保持率", "Good 中猜中比例"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        cells = [r["label"], f"{r['units_per_word']:.2f}"]
        cells += [f"{r[f'words_d{d}']:.0f}" for d in cps]
        cells += [f"{r[f'review_share_d{d}']:.0%}" for d in cps]
        cells += [f"{r['new_words_per_day_tail']:.1f}", f"{r['overdue_end']:.0f}",
                  f"{r['true_retention_end']:.2f}", f"{r['guess_share']:.1%}"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def check_fsrs() -> None:
    from datetime import datetime, timedelta, timezone
    from fsrs import Card, Rating, Scheduler

    sched = Scheduler(learning_steps=(), relearning_steps=(), enable_fuzzing=False, maximum_interval=36500)
    rng = random.Random(7)
    worst = 0.0
    for _ in range(300):
        card, now = Card(), datetime(2026, 1, 1, tzinfo=timezone.utc)
        s = d = None
        last = 0
        day = 0
        for _ in range(12):
            rating = rng.choice([AGAIN, GOOD])
            card, _ = sched.review_card(card, Rating(rating), now)
            if s is None:
                s, d = init_state(rating)
            else:
                s, d = review(s, d, day - last, rating)
            last = day
            worst = max(worst, abs(card.stability - s) / s, abs(card.difficulty - d))
            assert (card.due - now).days == interval_days(s, sched.desired_retention), "interval mismatch"
            gap = interval_days(s, sched.desired_retention) + rng.choice([0, 0, 1, 3, 10])
            day += gap
            now += timedelta(days=gap)
    assert worst < 1e-9, f"max deviation {worst}"
    print(f"FSRS-6 matches py-fsrs on 3600 reviews (max deviation {worst:.2e})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, help="write daily series of the base grid to this CSV")
    ap.add_argument("--check-fsrs", action="store_true")
    args = ap.parse_args()
    if args.check_fsrs:
        check_fsrs()
        return
    titles = ["## A. profile × 每日時間（180 天）", "## B. 敏感度（standard / 15 分 / 180 天）",
              "## C. 一年（15 分）"]
    all_rows = []
    for title, group in zip(titles, scenarios()):
        rows = [summarize(sc) for sc in group]
        all_rows += rows
        print(title + "\n\n" + fmt_table(rows, group[0].days) + "\n")
    if args.csv:
        with args.csv.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["scenario", "seed", "day", "studied", "review_seconds", "new_seconds",
                        "reviews", "new_units", "new_words", "overdue_left", "words_started"])
            for r in all_rows:
                for seed, res in zip(r["scenario"].seeds, r["runs"]):
                    for x, started in zip(res.daily, res.words_started):
                        w.writerow([r["label"], seed, x.day, int(x.studied), round(x.review_seconds),
                                    round(x.new_seconds), x.reviews, x.new_units, x.new_words,
                                    x.overdue_left, started])


if __name__ == "__main__":
    main()
