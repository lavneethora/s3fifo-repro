"""Trace registry for the S3-FIFO reproduction.

Both datasets are hosted in the public cache-datasets S3 bucket maintained by
the libCacheSim authors. libcachesim downloads an s3:// URI to a local cache on
first use, so the first run of any trace is slow and later runs are fast.

Paper reference: Table 1 of "FIFO queues are all you need for cache eviction",
SOSP '23. The paper excludes traces with fewer than 1 million requests from the
older datasets, which is why MSR has 14 files on S3 but 13 traces in the paper.
"""

import libcachesim as lcs

BUCKET = "s3://cache-datasets/cache_dataset_oracleGeneral"
# Same objects over plain HTTPS. libcachesim can fetch s3:// URIs itself, but its
# downloader runs at roughly 100 KB/s here while curl against the same bucket
# sustains about 6 MB/s, so traces are prefetched into its cache directory
# instead and the library then finds them locally.
HTTP_BASE = "https://cache-datasets.s3.amazonaws.com/cache_dataset_oracleGeneral"

# The paper's filter for the older datasets.
MIN_REQUESTS = 1_000_000

# MSR Cambridge 2007 block traces. Names are irregular, so they are listed out.
MSR_TRACES = [
    "msr_hm_0", "msr_prn_0", "msr_prn_1", "msr_proj_0", "msr_proj_1",
    "msr_proj_2", "msr_proj_4", "msr_prxy_0", "msr_prxy_1", "msr_src1_0",
    "msr_src1_1", "msr_usr_1", "msr_usr_2", "msr_web_2",
]

# CloudPhysics 2015 block traces, w01 through w106.
CLOUDPHYSICS_TRACES = [f"w{i:02d}" for i in range(1, 107)]

DATASETS = {
    "msr": {
        "label": "MSR",
        "prefix": "2007_msr",
        "suffix": ".oracleGeneral.zst",
        "traces": MSR_TRACES,
        # Paper Table 1: one-hit-wonder ratio at full trace / 10% / 1%.
        "paper_ohw": (0.56, 0.74, 0.86),
        "paper_n_traces": 13,
    },
    "cloudphysics": {
        "label": "CloudPhysics",
        "prefix": "2015_cloudphysics",
        "suffix": ".oracleGeneral.bin.zst",
        "traces": CLOUDPHYSICS_TRACES,
        "paper_ohw": (0.40, 0.71, 0.80),
        "paper_n_traces": 106,
    },
}


def trace_uri(dataset, name):
    """S3 URI for one trace."""
    d = DATASETS[dataset]
    return f"{BUCKET}/{d['prefix']}/{name}{d['suffix']}"


def open_trace(dataset, name):
    """Open a trace reader on the locally cached file.

    The local path is used rather than the s3:// URI on purpose. libcachesim
    resolves an s3:// URI through boto3, which is slow and, inside a
    multiprocessing worker, hangs outright. Traces are prefetched with curl
    anyway, so the file is already on disk.

    ignore_obj_size matches the paper's section 5, which sets cache sizes as a
    percentage of the number of objects and does not consider object size.
    """
    return lcs.TraceReader(
        trace=local_path(dataset, name),
        trace_type=lcs.TraceType.ORACLE_GENERAL_TRACE,
        reader_init_params=lcs.ReaderInitParam(ignore_obj_size=True),
    )


def iter_traces(dataset):
    """Yield (name, reader) for every trace in a dataset that clears the paper's
    minimum request count."""
    for name in DATASETS[dataset]["traces"]:
        reader = open_trace(dataset, name)
        if reader.get_num_of_req() < MIN_REQUESTS:
            continue
        yield name, reader


# ---------------------------------------------------------------------------
# Fast trace loading
#
# libcachesim reads traces through its C++ backend, but the one-hit-wonder
# analysis needs the raw object-id stream in Python. Pulling 400M requests
# through read_one_req() is far too slow, so the oracleGeneral records are
# decoded directly with numpy instead.
#
# An oracleGeneral record is a packed 24-byte struct:
#     uint32 timestamp, uint64 obj_id, uint32 obj_size, int64 next_access_vtime
# Verified against libcachesim: decoding msr_hm_0 this way yields 439187 unique
# objects, exactly matching the working set size the library reports.
# ---------------------------------------------------------------------------

import os
import subprocess

import numpy as np

RECORD = np.dtype([("ts", "<u4"), ("obj_id", "<u8"), ("sz", "<u4"), ("nxt", "<i8")])
CACHE_ROOT = os.path.expanduser(
    "~/.cache/libcachesim/hub/cache-datasets/cache_dataset_oracleGeneral"
)


def http_url(dataset, name):
    """Plain HTTPS URL for one trace."""
    d = DATASETS[dataset]
    return f"{HTTP_BASE}/{d['prefix']}/{name}{d['suffix']}"


def local_path(dataset, name, download=True):
    """Path of the locally cached trace, fetching it first if needed."""
    d = DATASETS[dataset]
    path = os.path.join(CACHE_ROOT, d["prefix"], f"{name}{d['suffix']}")
    if download and not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        partial = path + ".part"
        subprocess.run(
            ["curl", "-sSfL", "--retry", "3", "-o", partial, http_url(dataset, name)],
            check=True,
        )
        os.replace(partial, path)
    return path


def prefetch(dataset, jobs=4):
    """Download every trace in a dataset, a few at a time."""
    from concurrent.futures import ThreadPoolExecutor

    names = DATASETS[dataset]["traces"]
    missing = [n for n in names if not os.path.exists(local_path(dataset, n, download=False))]
    if not missing:
        print(f"  {DATASETS[dataset]['label']}: all {len(names)} traces already cached", flush=True)
        return
    print(f"  {DATASETS[dataset]['label']}: fetching {len(missing)} of {len(names)} traces",
          flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for name in pool.map(lambda n: (local_path(dataset, n), n)[1], missing):
            done += 1
            print(f"    [{done}/{len(missing)}] {name}", flush=True)


def load_fields(dataset, name, fields=("obj_id",)):
    """Return the requested record fields as numpy arrays.

    Decompression is streamed so that only the requested columns stay in
    memory, not the full 24-bytes-per-request raw buffer.
    """
    path = local_path(dataset, name)
    chunks = {f: [] for f in fields}
    stride = RECORD.itemsize
    with subprocess.Popen(["zstd", "-dc", path], stdout=subprocess.PIPE) as proc:
        leftover = b""
        while True:
            buf = proc.stdout.read(1 << 24)
            if not buf:
                break
            buf = leftover + buf
            usable = len(buf) - (len(buf) % stride)
            leftover = buf[usable:]
            block = np.frombuffer(buf[:usable], dtype=RECORD)
            for f in fields:
                chunks[f].append(block[f].copy())
    return tuple(
        np.concatenate(chunks[f]) if chunks[f] else np.empty(0, dtype=RECORD[f])
        for f in fields
    )


def load_obj_ids(dataset, name):
    """Return just the trace's object-id stream."""
    return load_fields(dataset, name, ("obj_id",))[0]


def load_prev_next(dataset, name):
    """Return (prev, nxt) index arrays for the trace.

    nxt is the oracleGeneral next_access_vtime field: for each request it holds
    the index of the next request for the same object, or -1 if there is none.
    prev is its inverse, built in a single O(n) scatter rather than by sorting,
    and holds the index of the previous request for the same object, or -1.

    With these two arrays, every quantity Experiment 1 needs becomes a masked
    numpy operation. A request is the first access to its object within a window
    starting at s when prev < s, and that object is a one-hit wonder inside a
    window ending at e when its nxt is -1 or at or past e.
    """
    (nxt,) = load_fields(dataset, name, ("nxt",))
    nxt = nxt.astype(np.int64)
    prev = np.full(len(nxt), -1, dtype=np.int64)
    has_next = nxt >= 0
    prev[nxt[has_next]] = np.flatnonzero(has_next)
    return prev, nxt
