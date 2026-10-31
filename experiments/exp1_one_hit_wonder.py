"""Experiment 1: one-hit-wonder ratio (paper Figure 3 and Table 1).

A "one-hit wonder" is an object requested exactly once in a sequence. The paper
argues these dominate web cache workloads, which is the entire motivation for
S3-FIFO's small FIFO queue.

Table 1 reports the ratio over the full trace and over random sub-sequences
containing 10% and 1% of the trace's objects. Section 3.1 defines a sub-sequence
by its *object* count, not its request count: "a random sub-sequence containing
10% objects". So for a fraction f we take the shortest window that contains
f * M distinct objects, where M is the number of distinct objects in the whole
trace, and measure the one-hit-wonder ratio inside that window. The paper
repeats this 100 times from random starting points and reports the mean.

Everything here is a masked numpy operation over the prev/next index arrays
described in traces.load_prev_next, so no object ids are needed and no window is
ever re-scanned.

This experiment runs no cache simulation at all. It is pure trace analysis, so
it is the cheapest way to confirm the trace decoding is correct before any of
the miss-ratio experiments depend on it.
"""

import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traces

# X axis of paper Figure 3. 1.0 is the full trace, which Table 1 also reports.
FRACTIONS = [0.001, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
REPEATS = 100
SEED = 0

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")


def window_firsts(prev, start, target_objects):
    """Indices of the first target_objects distinct objects seen from start, and
    the index one past the window. Returns (None, None) if the trace ends first.
    """
    n = len(prev)
    length = max(target_objects, 4096)
    while True:
        probe = min(start + length, n)
        firsts = np.flatnonzero(prev[start:probe] < start)
        if len(firsts) >= target_objects:
            firsts = firsts[:target_objects] + start
            return firsts, int(firsts[-1]) + 1
        if probe == n:
            return None, None
        length *= 2


def sampled_ratio(prev, nxt, fraction, n_objects, rng):
    """Mean one-hit-wonder ratio over REPEATS random sub-sequences."""
    target = max(int(round(fraction * n_objects)), 2)
    ratios = []
    attempts = 0
    while len(ratios) < REPEATS and attempts < REPEATS * 4:
        attempts += 1
        start = int(rng.integers(0, len(prev)))
        firsts, end = window_firsts(prev, start, target)
        if firsts is None:
            continue
        nxt_of_firsts = nxt[firsts]
        single = (nxt_of_firsts < 0) | (nxt_of_firsts >= end)
        ratios.append(float(single.mean()))
    return float(np.mean(ratios)) if ratios else float("nan")


def run(datasets=("msr", "cloudphysics")):
    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, "exp1_one_hit_wonder.csv")
    rows = []

    for dataset in datasets:
        meta = traces.DATASETS[dataset]
        for name in meta["traces"]:
            prev, nxt = traces.load_prev_next(dataset, name)
            if len(prev) < traces.MIN_REQUESTS:
                print(f"  skip {name}: {len(prev):,} requests, below the paper's 1M cutoff",
                      flush=True)
                continue

            is_first = prev < 0
            n_objects = int(is_first.sum())
            full_ratio = float((is_first & (nxt < 0)).sum()) / n_objects
            rng = np.random.default_rng(SEED)

            for fraction in FRACTIONS:
                ratio = (full_ratio if fraction >= 1.0
                         else sampled_ratio(prev, nxt, fraction, n_objects, rng))
                rows.append({
                    "dataset": dataset,
                    "trace": name,
                    "fraction": fraction,
                    "ohw_ratio": round(ratio, 6),
                    "n_requests": len(prev),
                    "n_objects": n_objects,
                })
            print(f"  {meta['label']:>12s} {name:<14s} {len(prev):>11,d} req  "
                  f"{n_objects:>10,d} obj  full={full_ratio:.3f}", flush=True)

    with open(out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {out} ({len(rows)} rows)", flush=True)
    return out


if __name__ == "__main__":
    run(tuple(sys.argv[1:]) or ("msr", "cloudphysics"))
