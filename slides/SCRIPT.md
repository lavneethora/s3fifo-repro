# Talk script

Word for word, slide by slide. Roughly 11 minutes at a normal speaking pace.
Say it in your own words once you know it; the point is that every sentence
here is one you could actually say out loud.

---

## 1. Cover (25s)

Hi, I'm Lavneet. The paper I picked is called "FIFO Queues Are All You Need for
Cache Eviction." It came out at SOSP in 2023, from a group at Carnegie Mellon
and Emory.

The title is a provocation, and I'll explain why in a minute. What I did was
take their experiments and run them again myself, on two of their datasets, to
see whether the numbers hold up.

---

## 2. Where the eviction algorithm sits (50s)

First, where this problem lives.

A cache sits between a client and a backend. It's fast, but it's small. Maybe
it holds one percent of your data.

If what you want is in the cache, that's a hit, and you get it in microseconds.
If it isn't, that's a miss, and you pay a full round trip to the backend, plus
you've just added load to the thing the cache was supposed to protect.

So the number you care about is the miss ratio. Misses divided by requests.

Here's the thing though. The cache is always full. Every time you put something
in, something else has to come out. The rule that picks what comes out is the
only real control you have over that number. And at the scale these companies
run at, one percentage point is worth a lot of servers.

---

## 3. Efficiency bought with complexity (55s)

So people have been working on this rule for about thirty years. ARC, 2Q, LIRS,
TinyLFU, and a long list of others. And almost all of them are built on top of
an LRU queue.

That buys you a better miss ratio. It costs you three things.

Memory. An LRU queue is a linked list, so every object carries two pointers. If
your objects are small, that's a real chunk of your cache gone to bookkeeping.

Throughput. LRU moves an object to the front of the queue every time you read
it. That's a write to shared state, so it needs a lock. On a cache hit. On the
operation that is supposed to be the fast one.

And complexity. These are hard to tune and hard to get right. The authors point
out that published LIRS implementations had two actual bugs in them.

So what happens in practice is that nobody deploys these. Real systems run
plain FIFO or LRU and just accept the worse miss ratio.

---

## 4. The key observation, 72% (45s)

Here's the observation the whole paper comes out of.

A one-hit wonder is an object that gets requested once and then never again.

If you measure that over a whole trace, it's about 26 percent. Which doesn't
sound like a crisis.

But a cache never sees a whole trace. It sees a window roughly the size of
itself. And if you measure over a window holding ten percent of the objects,
72 percent of them are requested exactly once.

So most of what you're admitting into your cache is garbage. And that changes
what the job is. It isn't really about working out which valuable object to
keep. It's about getting rid of the junk fast, before it occupies space that
something useful could have used.

---

## 5. Ask a cheaper question first (40s)

That's the shift. Every LRU variant is asking "which object here is least
valuable", and keeping that ranking up to date is what costs you.

S3-FIFO asks a cheaper question first. Has this thing been requested even once
since I let it in?

You can answer that with two bits instead of two pointers. A hit just bumps a
counter, so nothing moves, so you don't need a lock. And there's no LRU queue
anywhere in it.

The surprising part is the direction. Giving up LRU is supposed to cost you
efficiency. It doesn't. It buys it.

---

## 6. Three FIFO queues (70s)

Here's the actual algorithm.

S is small, ten percent of the cache. That's probation, where new objects land.

M is the main queue, the other ninety percent.

G is a ghost queue. It holds keys only, no data, so it's cheap to keep.

A new object goes into S. When S fills up, the object at the end leaves. If it
got requested while it was sitting in S, it's proved itself, so it moves into
M. If it never got requested, which is the common case, we drop it and keep
just its key in G.

Now here's the clever bit. If that key turns up again later, we know it isn't a
one-hit wonder after all. So this time it skips probation and goes straight
into M.

M itself works like a clock sweep. If an object's counter is above zero it goes
back round with the counter decremented, and when it hits zero it's evicted.

Those four lines are the entire algorithm. And notice that nothing moves when
you read something. That's where the speed comes from.

---

## 7. Two datasets, every trace (55s)

That's the paper. Here's what I actually ran.

They evaluate 6594 traces across fourteen datasets. That's several terabytes,
which I obviously can't do on a laptop.

So I took the two datasets that would fit, MSR and CloudPhysics, and I ran them
completely. Every trace, not a sample. That's 120 traces and 2.52 billion
requests, twelve algorithms, at two cache sizes. About twenty hours of compute.

The algorithms themselves are the authors' own code, through their simulator.
What I wrote is the harness around it.

One thing I want to flag now, because it explains everything later: both of the
datasets I could run are block storage workloads. The paper's evidence is
mostly web and key-value traffic, which is much more skewed. And skew is
exactly what this algorithm feeds on. So I'm testing it on its worst ground.

---

## 8. The paper contradicts itself twice (50s)

Before trusting any of that, I implemented the algorithm myself from their
pseudocode, to check I'd actually understood it.

And I found that the paper contradicts itself. Twice.

Section 4.1 says an object gets promoted if it was "accessed more than once".
The pseudocode says the counter has to be greater than one. Those are two
different things. And separately, the prose says the counter resets when you
promote, and the pseudocode never mentions resetting it.

So rather than guess, I built all four combinations and measured each one
against their actual C++.

The one that matches is this row. It takes the threshold from the pseudocode
and the counter reset from the prose. So neither half of the paper is right on
its own. If you implement this by reading only one of them, you get a
measurably different algorithm.

---

## 9. Result 1, one-hit wonders (45s)

Result one. This is the cheapest check I could do, because it needs no
simulation at all. You just count.

Top is their figure, bottom is mine.

The blue stars on my charts are their published numbers, dropped onto my data.
They land on my means, at all three window sizes, on both datasets. The worst
disagreement is 0.04.

My MSR traces also add up to 409.8 million requests, and they report 410
million. So I'm fairly confident I'm working from the same data. If this hadn't
lined up, nothing after it would have been worth anything.

---

## 10. Result 2, miss ratio reduction (60s)

This is the main result.

You can't just average raw miss ratios, because they vary enormously between
traces. So both of us measure each algorithm against FIFO on the same trace.

Left panels are the large cache. S3-FIFO comes first out of eleven algorithms,
and my mean is 14.8 percent. Their paper says 14. That's about as close as a
reproduction gets.

One more thing worth pointing at here. Look at the P10 bars, so the worst tenth
of traces. S3-FIFO stays positive. TinyLFU and LIRS go negative, which means on
those traces they're actually worse than plain FIFO. S3-FIFO is never much
worse than the baseline, and in production that matters more than being
slightly better on average.

On the right, the small cache, my ordering is different from theirs. I'll come
back to that in two slides.

---

## 11. Result 3, per dataset (45s)

This one's useful because the paper publishes my two datasets as their own
rows. So I can compare directly, instead of against an average over workloads I
never ran.

What my chart shows is that the win is carried by CloudPhysics. On MSR on its
own, ARC actually edges out S3-FIFO, 0.132 against 0.131, which is close enough
to be noise. On CloudPhysics S3-FIFO is clearly ahead, 0.151 against 0.110.

And if you look at their rows for those same two datasets, you see the same
pattern. The block workloads are where the lead is narrowest.

---

## 12. Result 4, how big should S be (50s)

Last result. The algorithm has basically one knob, which is how big the small
queue is. They set it to ten percent.

So I swept it. And my best value is five percent at the large cache, and
twenty-five at the small one. Not ten.

I almost reported that as a disagreement. But then I went back and reread what
they actually claim. Section 6.2 says the algorithm isn't sensitive to this
parameter, and their own figure shows a nearly flat line. They never say ten
percent is optimal.

My curve is flat in the same way, and ten percent is within about half a point
of my best at both cache sizes. So this confirms what they claimed. The lesson
for me was to check what was actually claimed before calling something a failed
reproduction.

---

## 13. Three gaps, one cause (45s)

So pulling the differences together. There are three, and they all come from
one decision.

2Q beats S3-FIFO at the small cache. My absolute gains are smaller than theirs.
And I have fourteen MSR traces where they report thirteen, although our request
totals match, so that one is just bookkeeping.

The first two come from the same place. The only two datasets small enough for
me to run are both block storage. Less skew, so less for quick demotion to
exploit. And at a tiny cache, objects get thrown out before they can prove
they're worth keeping, where 2Q reserves fixed space for new objects and
S3-FIFO doesn't.

Which I'd argue makes this a stronger result, not a weaker one. If I'd run the
CDN traces the numbers would look better and prove less.

---

## 14. Conclusion (40s)

So, does it hold up? Yes.

14.8 percent mean reduction over FIFO at the large cache size, first of eleven
algorithms, against their 14. And every one-hit-wonder value within 0.04.

It's qualified at a tiny cache on block workloads, and their own data predicts
that, so that's a limit on scope rather than a contradiction.

And along the way I found two places where the paper contradicts itself, and an
indexing inconsistency in their public trace files that would quietly break
anyone's analysis.

Forty lines of FIFO queues, beating thirty years of LRU variants, measured on
the workloads that suit them least.

Happy to take questions.

---

## Pacing

| Slides | Running time |
|---|---|
| 1 to 4 (setup and the observation) | about 2m 40s |
| 5 to 8 (the idea, the method, what I ran) | about 6m 35s |
| 9 to 12 (the four results) | about 9m 55s |
| 13 to 14 (differences and close) | about 11m 20s |

If you're running long, cut slide 11 down to one sentence and drop the P10
aside on slide 10. Don't cut slide 8; the two contradictions are the most
interesting thing you found.
