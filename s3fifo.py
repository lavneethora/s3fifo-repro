"""Our own implementation of S3-FIFO, transcribed from Algorithm 1 of
"FIFO queues are all you need for cache eviction" (SOSP '23).

The point of this file is to show the method is actually implemented here and
not just called in a library. libcachesim's C++ S3FIFO is used for the large
simulation runs because it is orders of magnitude faster; validate.py checks
this implementation against it.

Two places where the paper's prose and its pseudocode disagree, both exposed as
constructor flags so validate.py can test which one the reference implementation
follows:

1. Promotion threshold. Pseudocode line 23 promotes the tail of S to M when
   t.freq > 1. Section 4.1's prose says the object moves to M "if it is accessed
   more than once", and since freq starts at 0 and counts hits after insertion,
   that reads as freq >= 1. promote_threshold selects between them.

2. Clearing frequency on promotion. Section 4.1 says "its access bits are
   cleared during the move" from S to M. The pseudocode does not show this.
   reset_freq_on_promote selects between them.
"""

from collections import deque


class S3FIFO:
    def __init__(self, cache_size, small_ratio=0.10,
                 promote_threshold=1, reset_freq_on_promote=True):
        """cache_size is a number of objects, matching the paper's section 5,
        which sets cache sizes as a percentage of the objects in a trace and
        does not consider object size."""
        self.cache_size = int(cache_size)
        self.small_size = max(int(self.cache_size * small_ratio), 1)
        self.main_size = self.cache_size - self.small_size
        # Section 4.1: G holds the same number of entries as M, keys only.
        self.ghost_size = self.main_size
        self.promote_threshold = promote_threshold
        self.reset_freq_on_promote = reset_freq_on_promote

        self.S = deque()          # small FIFO queue, head is left
        self.M = deque()          # main FIFO queue, head is left
        self.G = deque()          # ghost FIFO queue, keys only
        self.ghost_set = set()
        self.freq = {}            # key -> access counter, capped at 3
        self.where = {}           # key -> "S" or "M"

        self.n_hit = 0
        self.n_miss = 0

    # -- Algorithm 1, line 1 ------------------------------------------------
    def read(self, key):
        """Process one request. Returns True on a cache hit."""
        if key in self.where:
            self.freq[key] = min(self.freq[key] + 1, 3)
            self.n_hit += 1
            return True
        self.n_miss += 1
        self._insert(key)
        return False

    # -- Algorithm 1, line 7 ------------------------------------------------
    def _insert(self, key):
        while len(self.S) + len(self.M) >= self.cache_size:
            self._evict()
        if key in self.ghost_set:
            # Section 4.2: the ghost entry is dropped once the object is requested.
            self.ghost_set.discard(key)
            self.M.appendleft(key)
            self.where[key] = "M"
        else:
            self.S.appendleft(key)
            self.where[key] = "S"
        self.freq[key] = 0

    # -- Algorithm 1, line 14 -----------------------------------------------
    def _evict(self):
        if len(self.S) >= self.small_size:
            self._evict_s()
        else:
            self._evict_m()

    # -- Algorithm 1, line 19 -----------------------------------------------
    def _evict_s(self):
        evicted = False
        while not evicted and len(self.S) > 0:
            t = self.S.pop()
            if self.freq[t] > self.promote_threshold:
                self.M.appendleft(t)
                self.where[t] = "M"
                if self.reset_freq_on_promote:
                    self.freq[t] = 0
                if len(self.M) > self.main_size:
                    self._evict_m()
            else:
                self._push_ghost(t)
                del self.where[t]
                del self.freq[t]
                evicted = True

    # -- Algorithm 1, line 31 -----------------------------------------------
    def _evict_m(self):
        evicted = False
        while not evicted and len(self.M) > 0:
            t = self.M.pop()
            if self.freq[t] > 0:
                self.M.appendleft(t)
                self.freq[t] -= 1
            else:
                del self.where[t]
                del self.freq[t]
                evicted = True

    def _push_ghost(self, key):
        if key in self.ghost_set:
            return
        self.G.appendleft(key)
        self.ghost_set.add(key)
        while len(self.G) > self.ghost_size:
            self.ghost_set.discard(self.G.pop())

    @property
    def miss_ratio(self):
        total = self.n_hit + self.n_miss
        return self.n_miss / total if total else 0.0


def simulate(obj_ids, cache_size, **kwargs):
    """Replay a stream of object ids and return the miss ratio."""
    cache = S3FIFO(cache_size, **kwargs)
    for key in obj_ids:
        cache.read(int(key))
    return cache.miss_ratio
