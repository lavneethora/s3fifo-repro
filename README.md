# Reproducing S3-FIFO (SOSP '23)

Course reproduction of:

> Juncheng Yang, Yazhuo Zhang, Ziyue Qiu, Yao Yue, K. V. Rashmi.
> **FIFO queues are all you need for cache eviction.**
> SOSP '23, Koblenz, Germany, pp. 130-149.
> https://doi.org/10.1145/3600006.3613147

S3-FIFO is a cache eviction algorithm built from three FIFO queues: a small one
`S` holding 10% of the cache, a main one `M` holding the other 90%, and a ghost
queue `G` that stores keys only. New objects enter `S` unless their key is in
`G`, in which case they go straight to `M`. Each object carries a 2-bit counter
capped at 3. The claim is that most web cache objects are "one-hit wonders" that
are never requested again, so a small queue can flush them out before they
pollute the cache, and that this beats far more complicated LRU-based designs.

## What is reproduced

The paper evaluates 6594 traces across 14 datasets, totalling several TB. Two of
those datasets are small enough to run on a laptop, and both are reproduced
**in full**, every trace, not a sample:

| Dataset | Traces | Requests | Download |
|---|---|---|---|
| MSR Cambridge 2007 | 14 | 410M | 1.6 GB |
| CloudPhysics 2015 | 106 | 2114M | 9.0 GB |

| Our figure | Paper figure | What it shows |
|---|---|---|
| `figures/fig3_one_hit_wonder.png` | Figure 3, Table 1 | One-hit-wonder ratio against sequence length |
| `figures/fig6_miss_ratio_reduction.png` | Figure 6 | Miss ratio reduction from FIFO, by percentile |
| `figures/fig7_per_dataset.png` | Figure 7 | Mean miss ratio reduction per dataset |
| `figures/fig11_small_queue.png` | Figure 11 | Sensitivity to the size of the small queue `S` |

Not reproduced, and out of scope for a laptop: Figure 8 (throughput scaling
across 16 CPU cores) and the Cachelib prototype results, which need a
dual-socket server, and Figure 9's flash write-amplification results.

## Setup

Needs Python 3.10 to 3.13 on arm64 macOS 15+ or Linux, where `libcachesim`
installs as a prebuilt wheel. On Python 3.14 pip falls back to compiling from
source, which pulls in CMake, Ninja, GLib and zstd, so pin 3.12.

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install libcachesim matplotlib pandas numpy
```

The `zstd` command line tool is also needed for the trace decoding in
experiment 1 (`brew install zstd`).

## Running

```bash
python run.py
```

Pick a step from the menu, or pass its number directly (`python run.py 4`).

1. **Download traces.** Fetches both datasets with `curl` into libcachesim's
   cache directory. About 11 GB. libcachesim can fetch `s3://` URIs itself but
   does so at roughly 100 KB/s here, where curl against the same bucket sustains
   about 6 MB/s.
2. **Experiment 1, one-hit-wonder ratio.** Pure trace analysis, no cache
   simulation. The cheapest check that the trace decoding is right, since its
   output is directly comparable to the paper's Table 1.
3. **Validate our S3-FIFO.** Compares `s3fifo.py`, transcribed by hand from the
   paper's Algorithm 1, against libcachesim's reference C++ implementation.
4. **Experiment 2, miss ratios.** The simulation workhorse: 12 algorithms over
   every trace at two cache sizes. Roughly 2 hours across both datasets on 8
   cores. Parallel and resumable, so it can be interrupted and restarted.
5. **Experiment 4, small queue sweep.** Varies the size of `S` to check the
   paper's 10% choice.
6. **Regenerate figures** from the CSVs in `results/`, without re-simulating.
7. **Compare against the paper**, printing the numbers that can be checked
   directly.

## Layout

```
run.py                        menu entry point
traces.py                     dataset registry, downloads, fast numpy trace loader
s3fifo.py                     our own S3-FIFO, from the paper's Algorithm 1
validate.py                   our implementation vs the libcachesim reference
plots.py                      one function per reproduced figure
experiments/
  exp1_one_hit_wonder.py      paper Figure 3 and Table 1
  exp2_miss_ratio.py          paper Figures 6 and 7
  exp4_small_queue.py         paper Figure 11
results/                      CSVs, so figures redraw without re-simulating
figures/                      output PNGs
```

## Notes on the paper

Two places where the paper's prose and its pseudocode disagree, both resolved
empirically in `validate.py` by testing all four combinations against the
reference implementation:

- **Promotion threshold.** Pseudocode line 23 promotes the tail of `S` to `M`
  when `freq > 1`. Section 4.1's prose says the object moves "if it is accessed
  more than once", which reads as `freq >= 1`. The pseudocode is right, and
  libcachesim's own `move_to_main_threshold` default of 2 agrees.
- **Clearing frequency on promotion.** Section 4.1 says the access bits are
  cleared when an object moves from `S` to `M`. The pseudocode does not show
  this. The prose is right.

Taking the pseudocode's threshold with the prose's reset matches the reference
implementation to within 0.0014 absolute miss ratio.

One difference in the trace data: the paper's Table 1 lists 13 MSR traces after
excluding any with fewer than 1 million requests, but the public dataset has 14
files that all clear that cutoff. Our 14 traces total 409.8M requests against
the paper's stated 410M, so the underlying data appears to be the same.
