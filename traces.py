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
    """Open a trace reader.

    ignore_obj_size matches the paper's section 5, which sets cache sizes as a
    percentage of the number of objects and does not consider object size.
    """
    return lcs.TraceReader(
        trace=trace_uri(dataset, name),
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
