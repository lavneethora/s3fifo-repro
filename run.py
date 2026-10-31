#!/usr/bin/env python3
"""Entry point for the S3-FIFO reproduction.

Run `python run.py` and pick a step, or pass a step number as an argument.
Every step is independent and reads from results/ so figures can be redrawn
without re-running any simulation.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))

DATASETS = ("msr", "cloudphysics")


def step_download():
    import traces
    for dataset in DATASETS:
        traces.prefetch(dataset, jobs=6)


def step_one_hit_wonder():
    import exp1_one_hit_wonder
    exp1_one_hit_wonder.run(DATASETS)


def step_validate():
    import validate
    validate.run()


def step_miss_ratio():
    import exp2_miss_ratio
    exp2_miss_ratio.run(DATASETS)


def step_small_queue():
    import exp4_small_queue
    exp4_small_queue.run(DATASETS)


def step_figures():
    import plots
    for fn in plots.ALL:
        try:
            fn()
        except FileNotFoundError as exc:
            print(f"  skipping {fn.__name__}: {os.path.basename(str(exc))} not generated yet")


def _has_rows(path):
    """True when a results CSV exists and holds more than just a header."""
    try:
        with open(path) as fh:
            return len(fh.readlines()) > 1
    except OSError:
        return False


def step_compare():
    """Print the numbers that are directly checkable against the paper."""
    import pandas as pd
    import plots

    print("\nPaper Table 1, one-hit-wonder ratio (mean over traces)")
    print(f"  {'dataset':<14s}{'length':>8s}{'paper':>8s}{'ours':>8s}{'diff':>8s}")
    path = os.path.join(ROOT, "results", "exp1_one_hit_wonder.csv")
    if _has_rows(path):
        df = pd.read_csv(path)
        for dataset, (full, ten, one) in plots.PAPER_OHW.items():
            sub = df[df.dataset == dataset]
            if sub.empty:
                continue
            for fraction, expected, label in ((1.0, full, "full"),
                                              (0.1, ten, "10%"),
                                              (0.01, one, "1%")):
                ours = sub[sub.fraction == fraction].ohw_ratio.mean()
                print(f"  {plots.DATASET_LABEL[dataset]:<14s}{label:>8s}"
                      f"{expected:>8.2f}{ours:>8.2f}{ours - expected:>+8.2f}")
    else:
        print("  not available yet, run step 2")

    print("\nMean miss ratio reduction from FIFO, large cache (10% of footprint)")
    path = os.path.join(ROOT, "results", "exp2_miss_ratio.csv")
    if _has_rows(path):
        df = plots.reduction_table()
        large = df[(df.cache_fraction == 0.1) & (df.algorithm != "FIFO")]
        means = large.groupby("algorithm").reduction.mean().sort_values(ascending=False)
        for rank, (algo, value) in enumerate(means.items(), start=1):
            mark = "  <-- S3-FIFO" if algo == "S3FIFO" else ""
            print(f"  {rank:>2d}. {algo:<12s}{value:>8.4f}{mark}")
        print(f"\n  traces: {large.trace.nunique()}, "
              f"datasets: {', '.join(sorted(large.dataset.unique()))}")
    else:
        print("  not available yet, run step 4")


STEPS = [
    ("Download traces (MSR 1.6 GB, CloudPhysics 9 GB)", step_download),
    ("Experiment 1: one-hit-wonder ratio (paper Figure 3 and Table 1)", step_one_hit_wonder),
    ("Validate our S3-FIFO against libcachesim's reference", step_validate),
    ("Experiment 2: miss ratios for all algorithms (paper Figures 6 and 7)", step_miss_ratio),
    ("Experiment 4: small FIFO queue size sweep (paper Figure 11)", step_small_queue),
    ("Regenerate all figures from existing results", step_figures),
    ("Compare our numbers against the paper", step_compare),
]


def main():
    choice = sys.argv[1] if len(sys.argv) > 1 else None
    if choice is None:
        print("\nS3-FIFO reproduction (Yang et al., SOSP '23)\n")
        for i, (label, _) in enumerate(STEPS, start=1):
            print(f"  {i}. {label}")
        print(f"  {len(STEPS) + 1}. Run everything in order")
        print("  0. Quit\n")
        choice = input("Step: ").strip()

    if choice in ("0", "q", "quit"):
        return
    if not choice.isdigit() or not 1 <= int(choice) <= len(STEPS) + 1:
        print("Pick one of the listed numbers.")
        return

    index = int(choice)
    selected = STEPS if index == len(STEPS) + 1 else [STEPS[index - 1]]
    for label, fn in selected:
        print(f"\n=== {label} ===", flush=True)
        fn()


if __name__ == "__main__":
    main()
