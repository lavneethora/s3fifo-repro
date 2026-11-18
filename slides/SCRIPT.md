# Talk script

Word for word, slide by slide. About 11 minutes if you don't rush.

## 1. Cover (25s)

Hey, I'm Lavneet. So the paper I picked is called FIFO Queues Are All You Need
for Cache Eviction, it's from SOSP 2023, a group at CMU and Emory.

The title is a bit of a flex and I'll get to why. What I did was basically run
their experiments again myself on two of their datasets, and see if I got the
same numbers.

## 2. Where the eviction algorithm sits (50s)

So first, where this problem actually sits.

You've got a client, a cache, and a backend. The cache is fast but it's small,
like maybe it holds one percent of your data.

If the thing you want is in there, that's a hit, you get it in microseconds. If
it's not, that's a miss, and now you've got to go all the way to the backend,
and you're also putting load on the exact thing the cache was supposed to
protect.

So the number you care about is the miss ratio, misses over requests.

But here's the thing, the cache is always full. So every time you put something
in, something else has to come out. And the rule that picks what comes out is
basically the only control you have over that number. At the scale these
companies run at, one percent is worth a lot of servers.

## 3. Efficiency bought with complexity (55s)

So people have been working on this rule for like thirty years. ARC, 2Q, LIRS,
TinyLFU, loads of them. And pretty much all of them are built on an LRU queue.

That gets you a better miss ratio, but it costs you three things.

Memory, because an LRU queue is a linked list, so every object is carrying two
pointers around. If your objects are small that's a decent chunk of your cache
just gone.

Throughput, because LRU moves the object to the front every single time you
read it. That's a write to shared state so it needs a lock. On a cache hit. On
the thing that's supposed to be the fast one.

And complexity, because these are hard to tune and hard to get right. The
authors point out that LIRS implementations people actually published had two
bugs in them.

So what happens in real life is nobody uses these. Companies run plain FIFO or
LRU and just live with the worse miss ratio.

## 4. The 72 percent observation (45s)

Okay so here's the observation the whole paper comes from.

A one-hit wonder is an object that gets requested once and then never again.

If you measure that over a whole trace it's about 26 percent. Which is fine,
whatever.

But a cache never sees a whole trace. It sees a window about its own size. And
if you measure over a window that holds ten percent of the objects, 72 percent
of them get requested exactly once.

So most of what you're putting in your cache is junk. And that kind of flips
what the job is. It's less about figuring out which good object to keep, and
more about getting the junk out fast before it takes up space something useful
could have used.

## 5. Ask a cheaper question first (40s)

So that's the shift. Every LRU variant is trying to answer which object is
least valuable, and keeping that ranking updated is what costs you.

S3-FIFO asks a cheaper question first, which is basically: has this thing been
requested even once since I let it in?

And you can answer that with two bits instead of two pointers. A hit just bumps
a counter so nothing moves, so you don't need a lock. And there's no LRU queue
anywhere in it.

The weird part is the direction. Giving up LRU is supposed to make your miss
ratio worse. It doesn't, it makes it better.

## 6. Three FIFO queues (70s)

Alright, the actual algorithm. Three FIFO queues.

S is the small one, ten percent of the cache. That's probation, new stuff lands
there.

M is the main one, the other ninety percent.

G is a ghost queue, it only holds keys, no actual data, so it's cheap.

New object goes into S. When S fills up the thing at the end has to leave. If
it got requested while it was sitting in S, cool, it proved itself, it moves to
M. If it never got requested, which is what usually happens, we throw it away
and just keep its key in G.

And here's the clever bit. If that key shows up again later, now we know it's
not a one-hit wonder. So this time it skips probation and goes straight to M.

M itself is like a clock sweep, if the counter's above zero it goes back round
and the counter drops by one, and when it hits zero it gets evicted.

Those four lines are the whole thing. And notice nothing moves when you read
something, that's where the speed comes from.

## 7. Two datasets, every trace (55s)

So that's the paper. Here's what I actually ran.

They test 6594 traces across fourteen datasets, which is a few terabytes, so
obviously that's not happening on my laptop.

So I took the two datasets that would fit, MSR and CloudPhysics, and I ran them
completely. Every trace, not a sample. That's 120 traces, 2.52 billion
requests, twelve algorithms, at two cache sizes. Took about twenty hours.

The algorithms are the authors' own code through their simulator, what I wrote
is the harness around it.

One thing I want to flag now because it explains basically everything later:
both datasets I could run are block storage. The paper's stuff is mostly web
and key-value, which is way more skewed. And skew is exactly what this
algorithm needs. So I'm testing it on the workloads that suit it worst.

## 8. The paper contradicts itself twice (50s)

Before I trusted any of that, I implemented the algorithm myself from their
pseudocode, just to check I'd actually understood it.

And I found the paper contradicts itself. Twice.

Section 4.1 says an object gets promoted if it was accessed more than once. The
pseudocode says the counter has to be greater than one. Those aren't the same
thing. And separately, the prose says the counter resets when you promote, and
the pseudocode doesn't mention resetting it at all.

So instead of guessing I just built all four versions and tested each one
against their actual C++.

The one that matches is this row. It takes the threshold from the pseudocode
and the reset from the prose. So neither half of the paper is right on its own.
If you implement this by reading only one of them, you get a slightly different
algorithm.

## 9. Result 1, one-hit wonders (45s)

Result one. This is the cheapest check I could do, because there's no
simulation at all, you're literally just counting.

Top is theirs, bottom is mine.

Those blue stars on my charts are their published numbers, I just dropped them
onto my data. They sit right on my means, all three window sizes, both
datasets. Worst gap is 0.04.

My MSR traces also come to 409.8 million requests and they report 410 million,
so I'm pretty confident I've got the same data. If this hadn't matched then
nothing after it would have meant anything.

## 10. Result 2, miss ratio reduction (60s)

This is the main result.

You can't just average raw miss ratios because they're all over the place
between traces, so both of us measure each algorithm against FIFO on the same
trace.

Left side is the large cache. S3-FIFO comes first out of eleven algorithms, my
mean is 14.8 percent, and their paper says 14. So that's about as close as
you're going to get.

One more thing worth looking at, the P10 bars, so that's the worst tenth of
traces. S3-FIFO stays positive. TinyLFU and LIRS go negative, which means on
those traces they're actually worse than just doing plain FIFO. S3-FIFO is
never much worse than the baseline, and honestly in production that probably
matters more than being slightly better on average.

Right side is the small cache, and my ordering is different from theirs. I'll
come back to that.

## 11. Result 3, per dataset (45s)

This one's handy because the paper breaks out my two datasets as their own
rows, so I can compare directly instead of against an average over workloads I
never ran.

What my chart shows is the win is basically carried by CloudPhysics. On MSR by
itself ARC actually beats S3-FIFO, 0.132 to 0.131, which is close enough that
it's probably noise. On CloudPhysics S3-FIFO is clearly ahead, 0.151 to 0.110.

And if you look at their rows for those same two datasets you see the same
thing. The block workloads are where the lead is smallest.

## 12. Result 4, how big should S be (50s)

Last result. The algorithm has basically one knob, how big the small queue is.
They set it at ten percent.

So I swept it. And my best value is five percent on the large cache and
twenty-five on the small one. Not ten.

I almost wrote this up as a disagreement, but then I went back and reread what
they actually claim. Section 6.2 says the algorithm isn't sensitive to this
parameter, and their own figure is a pretty flat line. They never say ten
percent is optimal.

My curve is flat the same way, and ten percent is within about half a point of
my best at both sizes. So this actually backs up what they said. Lesson for me
was to check what was actually claimed before calling something a failed
reproduction.

## 13. Three gaps, one cause (45s)

So pulling the differences together, there's three and they all come from one
decision.

2Q beats S3-FIFO at the small cache. My absolute numbers are smaller than
theirs. And I've got fourteen MSR traces where they say thirteen, though our
request totals match, so that one's probably just a counting thing on their
end.

The first two are the same cause. The only two datasets small enough for me to
run are both block storage. Less skew, so less for quick demotion to work with.
And at a tiny cache, objects get thrown out before they can prove they're worth
keeping, whereas 2Q keeps fixed space for new objects and S3-FIFO doesn't.

Which honestly I think makes this a stronger result, not a weaker one. If I'd
run the CDN traces the numbers would look better and prove less.

## 14. Conclusion (40s)

So does it hold up? Yeah, mostly.

14.8 percent mean reduction over FIFO at the large cache, first out of eleven
algorithms, against their 14. And every one-hit-wonder value within 0.04.

It's qualified at a tiny cache on block workloads, and their own data kind of
predicts that, so I'd call it a scope thing.

And along the way I found two spots where the paper contradicts itself, plus an
indexing inconsistency in their trace files that would quietly break anyone's
analysis.

Forty lines of FIFO queues beating thirty years of LRU variants, on the
workloads that suit them worst.

Yeah that's it, happy to take questions.

## Pacing

| Slides | Running time |
|---|---|
| 1 to 4 (setup and the observation) | about 2m 40s |
| 5 to 8 (the idea, the method, what I ran) | about 6m 35s |
| 9 to 12 (the four results) | about 9m 55s |
| 13 to 14 (differences and close) | about 11m 20s |

If you're running long, cut slide 11 to one sentence and drop the P10 bit on
slide 10. Don't cut slide 8, the two contradictions are the most interesting
thing you found.
