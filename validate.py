"""Check our S3-FIFO against libcachesim's reference C++ implementation.

The large simulation runs use libcachesim because it is far faster, so this is
the evidence that our own transcription of Algorithm 1 is faithful. It also
settles the two prose-versus-pseudocode ambiguities noted in s3fifo.py by
testing all four combinations and reporting which tracks the reference.

libcachesim's own defaults are a useful hint: move_to_main_threshold defaults to
2, meaning an object is promoted from S to M once its counter reaches 2, which
matches pseudocode line 23 (freq > 1) rather than the prose.
"""

import itertools
import os
import sys

import libcachesim as lcs
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s3fifo
import traces

TRACE = ("msr", "msr_hm_0")
MAX_REQUESTS = 2_000_000       # keep the pure-Python replay to a few seconds
SMALL_RATIO = 0.10             # the paper's choice for the small FIFO queue
CACHE_FRACTIONS = [0.001, 0.01, 0.1]


def reference_miss_ratio(dataset, name, cache_objects):
    reader = traces.open_trace(dataset, name)
    cache = lcs.S3FIFO(
        cache_size=int(cache_objects),
        small_size_ratio=SMALL_RATIO,
        ghost_size_ratio=1.0 - SMALL_RATIO,   # G holds as many entries as M
        move_to_main_threshold=2,
    )
    miss_ratio, _ = cache.process_trace(reader, start_req=0, max_req=MAX_REQUESTS)
    return miss_ratio


def run():
    dataset, name = TRACE
    ids = traces.load_obj_ids(dataset, name)[:MAX_REQUESTS]
    n_objects = len(np.unique(ids))
    print(f"trace {name}: {len(ids):,} requests, {n_objects:,} objects\n")

    variants = list(itertools.product([1, 0], [True, False]))
    header = "cache (objects)   reference"
    for threshold, reset in variants:
        header += f"   freq>{threshold},reset={str(reset)[0]}"
    print(header)

    worst = {v: 0.0 for v in variants}
    for fraction in CACHE_FRACTIONS:
        cache_objects = max(int(fraction * n_objects), 10)
        ref = reference_miss_ratio(dataset, name, cache_objects)
        line = f"{cache_objects:>15,d}   {ref:>9.4f}"
        for variant in variants:
            threshold, reset = variant
            ours = s3fifo.simulate(
                ids, cache_objects,
                small_ratio=SMALL_RATIO,
                promote_threshold=threshold,
                reset_freq_on_promote=reset,
            )
            delta = abs(ours - ref)
            worst[variant] = max(worst[variant], delta)
            line += f"   {ours:>15.4f}"
        print(line)

    print("\nworst absolute difference from the reference, by variant:")
    best = min(worst, key=worst.get)
    for variant, delta in sorted(worst.items(), key=lambda kv: kv[1]):
        threshold, reset = variant
        mark = "  <-- closest match" if variant == best else ""
        print(f"  freq > {threshold}, reset_freq_on_promote={reset}: {delta:.4f}{mark}")
    return best, worst[best]


if __name__ == "__main__":
    run()
