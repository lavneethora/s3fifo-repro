"""Experiment 4: how large should the small FIFO queue S be? (paper Figure 11)

Section 4.1 says S holds 10% of the cache, "based on experiments with 10 traces",
and Figure 11 shows the sensitivity. This sweeps the ratio and checks that 10%
really does sit at or near the optimum, which is the one tunable choice in an
otherwise parameter-free algorithm.

The ghost queue is kept the same size as M as the paper specifies, so it tracks
the small queue ratio rather than staying fixed.

FIFO is re-run here rather than read from experiment 2 so this experiment stands
on its own. Like experiment 2 it is parallel across traces and resumable.
"""

import csv
import multiprocessing as mp
import os
import sys
import time

import libcachesim as lcs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traces
from exp2_miss_ratio import CACHE_FRACTIONS, miss_ratio_reduction

SMALL_RATIOS = [0.01, 0.05, 0.10, 0.25, 0.50]
FIELDS = ["dataset", "trace", "cache_fraction", "small_ratio",
          "miss_ratio", "mr_fifo", "reduction", "n_objects"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "exp4_small_queue.csv")


def run_trace(job):
    dataset, name = job
    started = time.time()
    reader = traces.open_trace(dataset, name)
    if reader.get_num_of_req() < traces.MIN_REQUESTS:
        return dataset, name, [], 0.0

    n_objects = reader.get_working_set_size()[0]
    rows = []
    for fraction in CACHE_FRACTIONS:
        cache_objects = max(int(fraction * n_objects), 10)
        mr_fifo, _ = lcs.FIFO(cache_size=cache_objects).process_trace(reader)
        for ratio in SMALL_RATIOS:
            cache = lcs.S3FIFO(
                cache_size=cache_objects,
                small_size_ratio=ratio,
                ghost_size_ratio=1.0 - ratio,
                move_to_main_threshold=2,
            )
            miss_ratio, _ = cache.process_trace(reader)
            rows.append({
                "dataset": dataset,
                "trace": name,
                "cache_fraction": fraction,
                "small_ratio": ratio,
                "miss_ratio": round(miss_ratio, 6),
                "mr_fifo": round(mr_fifo, 6),
                "reduction": round(miss_ratio_reduction(miss_ratio, mr_fifo), 6),
                "n_objects": n_objects,
            })
    return dataset, name, rows, time.time() - started


def completed_traces():
    if not os.path.exists(OUT):
        return set()
    with open(OUT, newline="") as fh:
        return {(r["dataset"], r["trace"]) for r in csv.DictReader(fh)}


def run(datasets=("msr", "cloudphysics"), workers=None):
    os.makedirs(RESULTS, exist_ok=True)
    done = completed_traces()
    jobs = [(d, n) for d in datasets for n in traces.DATASETS[d]["traces"]
            if (d, n) not in done]
    if not jobs:
        print("  nothing to do, every trace is already in the CSV", flush=True)
        return OUT

    workers = workers or max(mp.cpu_count() - 2, 1)
    print(f"  {len(jobs)} traces to sweep on {workers} workers", flush=True)

    is_new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
            fh.flush()
        with mp.Pool(workers) as pool:
            for i, (dataset, name, rows, secs) in enumerate(
                    pool.imap_unordered(run_trace, jobs), start=1):
                if not rows:
                    continue
                writer.writerows(rows)
                fh.flush()
                best = max((r for r in rows if r["cache_fraction"] == 0.1),
                           key=lambda r: r["reduction"])
                print(f"  [{i}/{len(jobs)}] {name:<14s} {secs:6.1f}s  "
                      f"best S at 10% cache: {best['small_ratio']:g}", flush=True)

    print(f"\nwrote {OUT}", flush=True)
    return OUT


if __name__ == "__main__":
    run(tuple(sys.argv[1:]) or ("msr", "cloudphysics"))
