#!/usr/bin/env python3
"""Third round of simulations (results in docs/11).

1. Admission smoothing for a big paste: the learner adds 2,000 words at once.
   "Fill" admits new content whenever today's budget has time left (docs/09
   behaviour). "Lookahead" admits a new unit only if, for each of the next
   14 days, already-scheduled reviews plus the new unit's expected review
   footprint stay under 85% of the budget. Also run with missed days.

2. Slider with realistic accuracy: a meta-analysis of memory self-efficacy vs
   memory performance found r ~ 0.15 (Beaudoin & Desrichard 2011). With the
   population spread of docs/10 (sd of log m = 0.4), r = 0.15 means slider
   noise sd ~ 2.6 in log units. Compare against docs/10's optimistic settings.

Usage: python3 tools/simulate_admission_slider.py [--quick]
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_review_load import (  # noqa: E402
    GOOD, SENSE, USAGE, init_state, interval_days, review,
)
from simulate_exam_personalization import (  # noqa: E402
    POP_SIGMA, Learner, cost, run_learner,
)

BUDGET_MIN = 15
HORIZON = 14
CAP = 0.85


def good_chain_days(kind, retention: float = 0.9, horizon: int = HORIZON) -> list[int]:
    """Days (relative to introduction) of the reviews a unit needs if every answer is Good."""
    s, d = init_state(GOOD)
    day, days = 0, []
    while True:
        gap = interval_days(s, retention)
        day += gap
        if day > horizon:
            return days
        days.append(day)
        s, d = review(s, d, gap, GOOD)


class LookaheadLearner(Learner):
    """Learner whose new-content admission checks the projected review load."""

    def __init__(self, *a, lookahead: bool, **kw):
        super().__init__(*a, **kw)
        self.lookahead = lookahead

    def projected(self, day: int) -> list[float]:
        load = [0.0] * (HORIZON + 1)
        for u in self.units:
            off = max(u.due_day - day, 1)
            if off <= HORIZON:
                load[off] += cost(u.kind, False)
        for eligible, kind, _, _ in self.pending:
            for off in good_chain_days(kind):
                k = max(eligible - day, 0) + off
                if k <= HORIZON:
                    load[k] += cost(kind, False)
        return load

    def admits(self, kind, day: int, load: list[float]) -> bool:
        if not self.lookahead:
            return True
        return all(load[off] + cost(kind, False) <= CAP * self.budget for off in good_chain_days(kind))

    def study_day(self, day: int, new_word_units, words_available):
        spent = 0.0
        due = sorted((u for u in self.units if u.due_day <= day), key=lambda u: self.sched_r(u, day))
        for u in due:
            if spent >= self.budget:
                break
            spent += self.do_review(u, day)
        load = self.projected(day) if self.lookahead else None
        while spent < self.budget:
            idx = next((i for i, p in enumerate(self.pending) if p[0] <= day), None)
            if idx is not None:
                kind = self.pending[idx][1]
                if not self.admits(kind, day, load):
                    break
                _, kind, word, role = self.pending.pop(idx)
            else:
                if self.next_word >= words_available or not self.admits(SENSE, day, load):
                    break
                word, role, kind = self.next_word, "core", SENSE
                self.next_word += 1
                self.pending.append((day + 1, USAGE, word, "usage"))
            spent += self.introduce(kind, word, role, day)
            if load is not None:
                for off in good_chain_days(kind):
                    if off <= HORIZON:
                        load[off] += cost(kind, False)


def run_paste(lookahead: bool, adherence: float, seed: int, days: int = 120, words: int = 2000) -> dict:
    rng = random.Random(seed)
    lr = LookaheadLearner(rng, true_m=1.0, budget_minutes=BUDGET_MIN, desired_retention=0.9,
                          guess_aware=True, lookahead=lookahead)
    budget = lr.budget
    review_share, overdue = [], []
    study_rng = random.Random(seed + 999)
    for day in range(days):
        if study_rng.random() < adherence:
            due_ids = {id(u) for u in lr.units if u.due_day <= day}
            lr.study_day(day, None, words)
            reviewed = [u for u in lr.units if id(u) in due_ids and u.last_day == day]
            review_share.append(sum(cost(u.kind, False) for u in reviewed) / budget)
        overdue.append(sum(1 for u in lr.units if u.due_day <= day and u.last_day != day))
    late = lr.true_r_at_review[len(lr.true_r_at_review) // 2:]
    return {
        "words": lr.next_word,
        "peak_share": max(review_share),
        "days_full": sum(s >= 0.98 for s in review_share) / len(review_share),
        "overdue_max": max(overdue),
        "retention": statistics.fmean(late),
    }


def experiment_admission(seeds) -> str:
    lines = ["| 情境 | 新字准入 | 120 天開始字數 | 單日複習占比最高 | 複習吃滿整天的日子 | 最大積欠 units | 後半段實際記憶率 |",
             "|---|---|---|---|---|---|---|"]
    for adherence, label in ((1.0, "每天學"), (0.7, "約每週缺 2 天")):
        for lookahead, name in ((False, "有空就開新字（docs/09）"), (True, "預估未來 14 天負荷（≤85%）")):
            rs = [run_paste(lookahead, adherence, s) for s in seeds]
            m = {k: statistics.fmean(r[k] for r in rs) for k in ("words", "peak_share", "days_full", "overdue_max", "retention")}
            lines.append(f"| 一次貼 2,000 字 / 15 分 / {label} | {name} | {m['words']:.0f} | {m['peak_share']:.0%} | "
                         f"{m['days_full']:.0%} | {m['overdue_max']:.0f} | {m['retention']:.1%} |")
    return "\n".join(lines)


def experiment_slider(n: int) -> str:
    rng = random.Random(2026)
    learners = [math.exp(rng.gauss(0, POP_SIGMA)) for _ in range(n)]
    realistic = math.sqrt(POP_SIGMA ** 2 * (1 / 0.15 ** 2 - 1))
    lines = ["| 滑桿準確度 | 和真實記憶的相關 | 排程方式 | 估計誤差 d14 | d30 | d90 | 後半段實際記憶率 |",
             "|---|---|---|---|---|---|---|"]
    for sigma, label in ((0.2, "樂觀（docs/10）"), (0.6, "中等（docs/10）"), (realistic, "實證水準")):
        r = POP_SIGMA / math.sqrt(POP_SIGMA ** 2 + sigma ** 2)
        noise = random.Random(int(sigma * 1000))
        sliders = [m * math.exp(noise.gauss(0, sigma)) for m in learners]
        for name, v in (("只用滑桿", "slider"), ("滑桿＋作答資料", "slider+data")):
            rs = [run_learner(m, sl, sigma, v, 10 + i) for i, (m, sl) in enumerate(zip(learners, sliders))]

            def err(d):
                return statistics.fmean(math.exp(x[f"err{d}"]) - 1 for x in rs)
            lines.append(f"| {label} | {r:.2f} | {name} | {err(14):.0%} | {err(30):.0%} | {err(90):.0%} | "
                         f"{statistics.fmean(x['retention'] for x in rs):.1%} |")
    rs = [run_learner(m, 1.0, 1.0, "data", 10 + i) for i, m in enumerate(learners)]
    lines.append(f"| （不用滑桿） | — | 只用作答資料 | "
                 + " | ".join(f"{statistics.fmean(math.exp(x[f'err{d}']) - 1 for x in rs):.0%}" for d in (14, 30, 90))
                 + f" | {statistics.fmean(x['retention'] for x in rs):.1%} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    print("## 實驗三：大量加入時的新字准入\n")
    print(experiment_admission((1,) if args.quick else (1, 2, 3)) + "\n")
    print("## 實驗四：滑桿在實證準確度下的效果（core / 15 分 / 90 天）\n")
    print(experiment_slider(12 if args.quick else 40))


if __name__ == "__main__":
    main()
