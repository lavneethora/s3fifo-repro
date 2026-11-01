"""Figures for the S3-FIFO reproduction.

Each function regenerates one figure from a results CSV, so plots can be redrawn
without re-running any simulation. File names say which paper figure each one
corresponds to.
"""

import os

import matplotlib
matplotlib.use("Agg")
# Load the Agg backend eagerly. matplotlib normally defers this until the first
# figure is created, but libcachesim gets imported in between (reduction_table
# pulls in exp2_miss_ratio), and importing it after matplotlib but before the
# backend has loaded breaks matplotlib's freetype linkage with
# "module 'matplotlib.ft2font' has no attribute '__path__'".
import matplotlib.backends.backend_agg  # noqa: F401
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "results")
FIGURES = os.path.join(ROOT, "figures")

DATASET_LABEL = {"msr": "MSR", "cloudphysics": "CloudPhysics"}
# Paper Table 1, one-hit-wonder ratio at full trace / 10% / 1%.
PAPER_OHW = {"msr": (0.56, 0.74, 0.86), "cloudphysics": (0.40, 0.71, 0.80)}


def _save(fig, name, top=0.90):
    fig.tight_layout(rect=[0, 0, 1, top])
    os.makedirs(FIGURES, exist_ok=True)
    path = os.path.join(FIGURES, name)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path}", flush=True)
    return path


def fig3_one_hit_wonder(csv=None):
    """Paper Figure 3: one-hit-wonder ratio across traces, by sequence length."""
    df = pd.read_csv(csv or os.path.join(RESULTS, "exp1_one_hit_wonder.csv"))
    datasets = [d for d in ("msr", "cloudphysics") if d in set(df.dataset)]
    fig, axes = plt.subplots(1, len(datasets), figsize=(5.2 * len(datasets), 3.6),
                             squeeze=False)

    for ax, dataset in zip(axes[0], datasets):
        sub = df[df.dataset == dataset]
        fractions = sorted(sub.fraction.unique())
        data = [sub[sub.fraction == f].ohw_ratio.values for f in fractions]
        positions = np.arange(len(fractions))

        ax.boxplot(data, positions=positions, widths=0.55, whis=(10, 90),
                   showfliers=False, showmeans=True,
                   meanprops=dict(marker="^", markerfacecolor="tab:red",
                                  markeredgecolor="tab:red", markersize=7),
                   medianprops=dict(color="black"))

        # The three sequence lengths the paper tabulates.
        full, ten, one = PAPER_OHW[dataset]
        for frac, value in ((1.0, full), (0.1, ten), (0.01, one)):
            if frac in fractions:
                ax.scatter([fractions.index(frac)], [value], marker="*", s=150,
                           color="tab:blue", zorder=5,
                           label="paper Table 1" if frac == 1.0 else None)

        ax.set_xticks(positions)
        ax.set_xticklabels([f"{f:g}" for f in fractions], rotation=45)
        ax.set_xlabel("Fraction of objects in the trace")
        ax.set_ylabel("One-hit-wonder ratio")
        ax.set_ylim(0, 1)
        ax.set_title(f"{DATASET_LABEL[dataset]} ({sub.trace.nunique()} traces)")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(loc="lower left", fontsize=8)

    fig.suptitle("Reproduction of paper Figure 3: one-hit-wonder ratio "
                 "(box = P25 to P75, whiskers = P10 and P90, triangle = mean)",
                 fontsize=10)
    return _save(fig, "fig3_one_hit_wonder.png", top=0.88)


def reduction_table(csv=None):
    """Miss ratio reduction from FIFO, one row per trace, cache size and algorithm."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "experiments"))
    from exp2_miss_ratio import miss_ratio_reduction

    df = pd.read_csv(csv or os.path.join(RESULTS, "exp2_miss_ratio.csv"))
    baseline = (df[df.algorithm == "FIFO"]
                .set_index(["dataset", "trace", "cache_fraction"]).miss_ratio)
    keys = list(zip(df.dataset, df.trace, df.cache_fraction))
    df["mr_fifo"] = baseline.reindex(keys).values
    df["reduction"] = [miss_ratio_reduction(a, f)
                       for a, f in zip(df.miss_ratio, df.mr_fifo)]
    return df


def fig6_percentiles(csv=None):
    """Paper Figure 6: miss ratio reduction from FIFO at several percentiles."""
    df = reduction_table(csv)
    df = df[df.algorithm != "FIFO"]
    stats = {
        "P10": lambda s: s.quantile(0.10), "P25": lambda s: s.quantile(0.25),
        "Median": lambda s: s.median(), "Mean": lambda s: s.mean(),
        "P75": lambda s: s.quantile(0.75), "P90": lambda s: s.quantile(0.90),
    }
    fractions = sorted(df.cache_fraction.unique(), reverse=True)
    fig, axes = plt.subplots(1, len(fractions), figsize=(7.5 * len(fractions), 4.2),
                             squeeze=False)

    for ax, fraction in zip(axes[0], fractions):
        sub = df[df.cache_fraction == fraction]
        order = (sub.groupby("algorithm").reduction.mean()
                 .sort_values(ascending=False).index.tolist())
        width = 0.8 / len(stats)
        x = np.arange(len(order))
        for i, (label, fn) in enumerate(stats.items()):
            vals = [fn(sub[sub.algorithm == a].reduction) for a in order]
            ax.bar(x + i * width - 0.4 + width / 2, vals, width, label=label)

        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=45, ha="right")
        ax.set_ylabel("Miss ratio reduction from FIFO")
        ax.set_title(f"{'Large' if fraction >= 0.1 else 'Small'} cache, "
                     f"{fraction:g} of trace footprint "
                     f"({sub.trace.nunique()} traces)")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=8, ncol=3)

    fig.suptitle("Reproduction of paper Figure 6: miss ratio reduction from FIFO",
                 fontsize=11)
    return _save(fig, "fig6_miss_ratio_reduction.png")


def fig7_per_dataset(csv=None):
    """Paper Figure 7: mean miss ratio reduction per dataset."""
    df = reduction_table(csv)
    df = df[df.algorithm != "FIFO"]
    fractions = sorted(df.cache_fraction.unique(), reverse=True)
    datasets = [d for d in ("msr", "cloudphysics") if d in set(df.dataset)]
    fig, axes = plt.subplots(1, len(fractions), figsize=(7.5 * len(fractions), 4.2),
                             squeeze=False)

    for ax, fraction in zip(axes[0], fractions):
        sub = df[df.cache_fraction == fraction]
        order = (sub.groupby("algorithm").reduction.mean()
                 .sort_values(ascending=False).index.tolist())
        width = 0.8 / len(datasets)
        x = np.arange(len(order))
        for i, dataset in enumerate(datasets):
            vals = [sub[(sub.algorithm == a) & (sub.dataset == dataset)]
                    .reduction.mean() for a in order]
            ax.bar(x + i * width - 0.4 + width / 2, vals, width,
                   label=DATASET_LABEL[dataset])

        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=45, ha="right")
        ax.set_ylabel("Mean miss ratio reduction from FIFO")
        ax.set_title(f"{'Large' if fraction >= 0.1 else 'Small'} cache, "
                     f"{fraction:g} of trace footprint")
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Reproduction of paper Figure 7: mean miss ratio reduction per dataset",
                 fontsize=11)
    return _save(fig, "fig7_per_dataset.png")


def fig11_small_queue(csv=None):
    """Paper Figure 11: sensitivity to the size of the small FIFO queue S."""
    df = pd.read_csv(csv or os.path.join(RESULTS, "exp4_small_queue.csv"))
    fractions = sorted(df.cache_fraction.unique(), reverse=True)
    fig, axes = plt.subplots(1, len(fractions), figsize=(5.6 * len(fractions), 4.0),
                             squeeze=False)

    for ax, fraction in zip(axes[0], fractions):
        sub = df[df.cache_fraction == fraction]
        ratios = sorted(sub.small_ratio.unique())
        for dataset in sorted(sub.dataset.unique()):
            means = [sub[(sub.small_ratio == r) & (sub.dataset == dataset)]
                     .reduction.mean() for r in ratios]
            ax.plot(ratios, means, marker="o", label=DATASET_LABEL[dataset])

        ax.axvline(0.10, color="tab:red", linestyle="--", linewidth=1,
                   label="paper's choice, 10%")
        ax.set_xscale("log")
        ax.set_xticks(ratios)
        ax.set_xticklabels([f"{r:g}" for r in ratios])
        ax.set_xlabel("Size of small FIFO queue S (fraction of cache)")
        ax.set_ylabel("Mean miss ratio reduction from FIFO")
        ax.set_title(f"{'Large' if fraction >= 0.1 else 'Small'} cache, "
                     f"{fraction:g} of trace footprint")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)

    fig.suptitle("Reproduction of paper Figure 11: effect of the small queue size",
                 fontsize=11)
    return _save(fig, "fig11_small_queue.png")


ALL = [fig3_one_hit_wonder, fig6_percentiles, fig7_per_dataset, fig11_small_queue]
