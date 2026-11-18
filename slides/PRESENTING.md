# Presenting this: cheat sheet

## The whole project in 60 seconds

A cache is too small to hold everything, so every time you add something you
must throw something out. The rule that picks the victim is the eviction
algorithm, and for thirty years that rule has been LRU or something built on
LRU.

This paper says: don't use LRU at all. Use three plain FIFO queues. It wins
anyway, and it's simpler.

I re-ran their experiments on two of their fourteen datasets, every trace, and
checked whether their numbers hold up. They mostly did.

## Three numbers to know cold

| Number | What it is |
|---|---|
| **14.8%** | Our mean miss ratio reduction over FIFO at the large cache. The paper says 14%. This is the headline. |
| **72%** | Of objects in a window holding 10% of a trace's objects are requested exactly once. This is why the algorithm works. |
| **120 traces, 2.52B requests** | What we ran. Two datasets, complete, not sampled. |

## How S3-FIFO works (say it like this)

Three queues: **S** is small, 10% of the cache, where new objects land on
probation. **M** is the main queue, the other 90%. **G** is a ghost queue that
holds keys only, no data.

A new object goes into S. If it gets requested while it's in S, it's proved
itself and moves to M. If it never gets requested, it's dropped and only its
key goes to G. If that key shows up again later, we know it isn't junk, so it
skips probation and goes straight to M.

A cache hit just increments a 2-bit counter. Nothing moves. That's why it needs
no lock, and that's where the speed comes from.

## Presenting

- Open `slides/index.html` in Chrome, press **N** for speaker notes. Or use
  PowerPoint presenter view, the notes are in there too.
- The notes are written as what to actually say, not bullet points.
- 14 slides. Don't read them aloud, they're keywords.
- The story in order: the problem with LRU, the one-hit-wonder observation, the
  three queues, what I ran, four results, where I differ, conclusion.

## Likely questions

**What is a one-hit wonder?**
An object requested once and never again. Over a whole trace about 26% of
objects are one-hit wonders, but a cache only sees a window about its own size,
and in a window that size it's 72%. Most of what you admit is junk.

**Why is FIFO faster than LRU?**
LRU has to move the object to the head of the queue on every hit. That's a
write to shared state, so it needs a lock, on the operation that's supposed to
be fast. S3-FIFO just increments a counter and moves nothing.

**What's the ghost queue for?**
It's the cache's memory of what it has already seen and thrown away. Keys only,
no data, so it's cheap. If a key comes back, that object isn't a one-hit wonder
after all, so it skips probation.

**Did your results match the paper?**
Yes on the main claim. All six of their one-hit-wonder values reproduced within
0.04, and at the large cache size S3-FIFO came first of eleven algorithms with
a mean of 14.8% against their stated 14%. One difference: at the very small
cache size I got 2Q slightly ahead, 5.48% against 5.33%, where they had
S3-FIFO first.

**Why did that differ?**
Both datasets I could run are block storage workloads. The paper's set is
mostly web and key-value, which are far more skewed, and skew is exactly what
this algorithm exploits. So I tested it on the workloads that suit it least. At
a tiny cache, objects get evicted before they can prove reuse, and 2Q reserves
fixed space for new objects where S3-FIFO doesn't.

**Why only two datasets?**
The full set is 6594 traces across fourteen datasets, several terabytes. These
two are about 11 GB, so they fit on a laptop, and I ran both completely rather
than sampling.

**What did you implement versus what did you reuse?**
The algorithms are the authors' own, through their libCacheSim. I wrote the
experiment harness, and I also implemented S3-FIFO myself from their Algorithm
1 to check I understood it. Mine matches their C++ to within 0.0014 miss ratio.

**Did you find anything wrong with the paper?**
Two things. Their prose and their pseudocode contradict each other in two
places: the promotion threshold and whether the counter resets. The correct
implementation takes one detail from each, so neither half of the paper is
right on its own. Separately, their public trace files index the next-access
field from 0 in one dataset and from 1 in another, which silently corrupts your
analysis if you assume one convention.

**Why is the small queue 10%?**
The paper picked it from experiments on ten traces. I swept it and found the
best value was 5% at the large cache and 25% at the small one. But the paper
never claims 10% is optimal, it claims the algorithm isn't sensitive to it, and
my curve is flat too, so this confirms their claim rather than contradicting it.

**What's "miss ratio reduction from FIFO"?**
Absolute miss ratios vary hugely between traces, so you can't average them.
Instead you measure each algorithm against FIFO on the same trace:
`(MR_fifo - MR_algo) / MR_fifo`. The paper flips the denominator when an
algorithm is worse than FIFO, which bounds it between -1 and 1 so outliers
can't dominate the mean.

**What would you do next?**
Run the web and key-value datasets, which is where the paper's advantage is
largest, and where I'd expect the small-cache result to flip back.

## If you don't know an answer

Say what you did measure. "I didn't test that, but what I did find was..." is a
perfectly good answer. You ran 2.52 billion requests; you have data to fall
back on.
