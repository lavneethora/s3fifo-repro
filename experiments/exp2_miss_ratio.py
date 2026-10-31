"""Experiment 2: miss ratios for every algorithm, trace and cache size.

This is the simulation workhorse. Experiments 3 and 4 and the Figure 6 and 7
plots all read the CSV it produces, so the expensive replaying happens once.

Paper section 5.2 presents two representative cache sizes, a large one at 10%
of the trace footprint and a small one at 0.1%, where footprint means the number
of distinct objects in the trace. Object sizes are ignored, matching the paper.

The headline metric is miss ratio reduction relative to FIFO. The paper defines
it asymmetrically so that it stays within [-1, 1] and outliers cannot dominate
the mean:

    if MR_algo <= MR_fifo:   (MR_fifo - MR_algo) / MR_fifo
    else:                   -(MR_algo - MR_fifo) / MR_algo

Runs are parallel across traces and resumable: a trace already present in the
output CSV is skipped, so a long run can be interrupted and restarted.
"""

import csv
import multiprocessing as mp
import os
import sys
import time

import libcachesim as lcs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import traces

# FIFO first: it is the baseline every reduction is measured against.
ALGORITHMS = [
    "FIFO", "LRU", "Clock", "ARC", "TwoQ", "SLRU",
    "LIRS", "WTinyLFU", "LeCaR", "LHD", "Cacheus", "S3FIFO",
]

# Paper section 4.1: S is 10% of the cache, M is the other 90%, and the ghost
# queue G holds as many entries as M. libcachesim's own default for
# small_size_ratio is 0.2, so this has to be set explicitly.
S3FIFO_PARAMS = dict(small_size_ratio=0.10, ghost_size_ratio=0.90,
                     move_to_main_threshold=2)

CACHE_FRACTIONS = [0.1, 0.001]      # large and small, per paper section 5.2
FIELDS = ["dataset", "trace", "cache_fraction", "algorithm",
          "miss_ratio", "n_requests", "n_objects"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(RESULTS, "exp2_miss_ratio.csv")


def miss_ratio_reduction(mr_algo, mr_fifo):
    """The paper's asymmetric reduction metric, bounded to [-1, 1]."""
    if mr_fifo <= 0 and mr_algo <= 0:
        return 0.0
    if mr_algo <= mr_fifo:
        return (mr_fifo - mr_algo) / mr_fifo if mr_fifo > 0 else 0.0
    return -(mr_algo - mr_fifo) / mr_algo if mr_algo > 0 else 0.0


def run_trace(job):
    """Replay one trace under every algorithm and cache size."""
    dataset, name = job
    started = time.time()
    reader = traces.open_trace(dataset, name)
    n_requests = reader.get_num_of_req()
    if n_requests < traces.MIN_REQUESTS:
        return dataset, name, [], 0.0

    n_objects = reader.get_working_set_size()[0]
    rows = []
    for fraction in CACHE_FRACTIONS:
        cache_objects = max(int(fraction * n_objects), 10)
        for algo in ALGORITHMS:
            kwargs = dict(S3FIFO_PARAMS) if algo == "S3FIFO" else {}
            cache = getattr(lcs, algo)(cache_size=cache_objects, **kwargs)
            miss_ratio, _ = cache.process_trace(reader)
            rows.append({
                "dataset": dataset,
                "trace": name,
                "cache_fraction": fraction,
                "algorithm": algo,
                "miss_ratio": round(miss_ratio, 6),
                "n_requests": n_requests,
                "n_objects": n_objects,
            })
    return dataset, name, rows, time.time() - started


def completed_traces():
    """(dataset, trace) pairs already in the output CSV."""
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
    if done:
        print(f"  resuming, {len(done)} traces already done", flush=True)

    workers = workers or max(mp.cpu_count() - 2, 1)
    print(f"  {len(jobs)} traces to simulate on {workers} workers", flush=True)

    is_new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        with mp.Pool(workers) as pool:
            for i, (dataset, name, rows, secs) in enumerate(
                    pool.imap_unordered(run_trace, jobs), start=1):
                if not rows:
                    print(f"  [{i}/{len(jobs)}] skip {name}, below the 1M request cutoff",
                          flush=True)
                    continue
                writer.writerows(rows)
                fh.flush()
                best = min((r for r in rows if r["cache_fraction"] == 0.1),
                           key=lambda r: r["miss_ratio"])
                print(f"  [{i}/{len(jobs)}] {name:<14s} {secs:6.1f}s  "
                      f"best at 10%: {best['algorithm']} ({best['miss_ratio']:.4f})",
                      flush=True)

    print(f"\nwrote {OUT}", flush=True)
    return OUT


if __name__ == "__main__":
    run(tuple(sys.argv[1:]) or ("msr", "cloudphysics"))
