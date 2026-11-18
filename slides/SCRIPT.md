# Talk cues

Prompts, not sentences. Say them however they come out. About 11 minutes.

## Numbers you can't fumble

    14.8%     your mean reduction over FIFO, large cache
    14%       what the paper says
    72%       one-hit wonders in a cache-sized window
    26%       one-hit wonders over a whole trace
    0.04      worst gap on the Table 1 values
    120 traces, 2.52 billion requests
    0.132 vs 0.131    ARC vs you on MSR alone
    0.151 vs 0.110    you vs ARC on CloudPhysics

## 1. Cover

- your name, paper title, SOSP 2023, CMU and Emory
- what you did: reran their experiments on two of their datasets

## 2. Where the eviction algorithm sits

- client, cache, backend
- cache is fast but small, holds maybe 1% of the data
- hit = microseconds
- miss = full round trip, plus load on the backend you were protecting
- miss ratio = misses over requests
- cache is always full, so every insert forces an evict
- that rule is the only real lever you have

## 3. Efficiency bought with complexity

- 30 years of LRU variants: ARC, 2Q, LIRS, TinyLFU
- memory cost: two pointers per object, hurts when objects are small
- throughput cost: moves on every read, so a lock on the hot path
- complexity cost: published LIRS code had two actual bugs
- result: nobody deploys them, real systems run FIFO or LRU

## 4. The 72 percent slide

- one-hit wonder = requested once, never again
- whole trace: 26%
- but a cache only ever sees a window its own size
- window holding 10% of objects: 72%
- so the job is dumping junk fast, not ranking the good stuff

## 5. Ask a cheaper question first

- LRU asks "which is least valuable", expensive to keep updated
- this asks "has it been requested even once since I let it in"
- two bits instead of two pointers
- hit just bumps a counter, nothing moves, no lock
- the surprise: dropping LRU makes it better, not worse

## 6. Three FIFO queues

- S, small, 10%, probation
- M, main, 90%
- G, ghost, keys only, no data
- new object goes to S
- S fills: got requested? to M. never requested? dropped, key to G
- that key comes back later: skip probation, straight to M
- M is a clock sweep: counter above zero goes round, zero gets evicted
- nothing moves on a read, that's where the speed is

## 7. Two datasets, every trace

- theirs: 6594 traces, 14 datasets, several TB
- mine: MSR and CloudPhysics, complete, every trace not a sample
- 120 traces, 2.52B requests, 12 algorithms, 2 cache sizes, ~20 hours
- their algorithms through their simulator, I wrote the harness
- flag it here: both of mine are block workloads
- theirs is mostly web and key-value, way more skewed
- skew is what the algorithm needs, so you tested it on its worst ground

## 8. The paper contradicts itself twice

- you implemented it yourself from the pseudocode to check you understood it
- 4.1 says "accessed more than once", pseudocode says counter greater than one
- prose says the counter resets on promotion, pseudocode never mentions it
- so you built all four versions and tested each against their C++
- the matching row takes the threshold from the pseudocode, the reset from the prose
- neither half of the paper is right on its own

## 9. Result 1, one-hit wonders

- cheapest check, no simulation, just counting
- top is theirs, bottom is yours
- blue stars are their published numbers dropped on your data
- they sit on your means, three window sizes, both datasets
- worst gap 0.04
- your MSR comes to 409.8M requests, they say 410M, so same data
- if this hadn't matched, nothing after it would mean anything

## 10. Result 2, miss ratio reduction

- can't average raw miss ratios, too spread out, so measure against FIFO per trace
- left panels, large cache
- first of eleven, mean 14.8%, their paper says 14%
- point at the P10 bars, the worst tenth of traces
- yours stays positive, TinyLFU and LIRS go negative
- negative means worse than plain FIFO on those traces
- never much worse than baseline matters more in production than a better average
- right panels, small cache, your order is different, say you'll come back to it

## 11. Result 3, per dataset

- paper breaks your two datasets out as their own rows, so you can compare directly
- the win is carried by CloudPhysics
- MSR alone: ARC 0.132, S3-FIFO 0.131, close enough to be noise
- CloudPhysics: 0.151 against 0.110
- their rows show the same shape, block is where the lead is smallest

## 12. Result 4, how big should S be

- one knob, the size of the small queue, they set it at 10%
- you swept it: best was 5% large cache, 25% small cache
- you nearly called it a disagreement
- then reread 6.2: they claim it isn't sensitive, their figure is flat
- they never claim 10% is optimal
- yours is flat too, 10% is within half a point of your best at both sizes
- so it backs them up, lesson was to check what was actually claimed

## 13. Three gaps, one cause

- 2Q beats you at the small cache
- your absolute gains are smaller
- you have 14 MSR traces, they report 13, totals match so it's a counting thing
- first two are the same cause: both your datasets are block, less skew
- tiny cache evicts objects before they can prove reuse
- 2Q reserves fixed space for new objects, S3-FIFO doesn't
- makes it a stronger result: CDN traces would look better and prove less

## 14. Conclusion

- does it hold up: yes, mostly
- 14.8% against their 14%, first of eleven
- every one-hit-wonder value within 0.04
- qualified at a tiny cache on block workloads, their own data predicts it
- what you found: two contradictions, plus the 0 versus 1 indexing split in their traces
- closing line: forty lines of FIFO beating thirty years of LRU variants, on the workloads that suit them worst
- questions

## Pacing

    slides 1 to 4     about 2m 40s
    slides 5 to 8     about 6m 35s
    slides 9 to 12    about 9m 55s
    slides 13 to 14   about 11m 20s

Running long: cut slide 11 to one line, drop the P10 bit on slide 10. Keep
slide 8, it's the most interesting thing you found.
