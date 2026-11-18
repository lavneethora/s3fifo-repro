# Speaking script

14 slides. Roughly 15 to 16 minutes at a normal pace. If you need it closer to
10, the cuts are listed at the bottom.

## Slide 1: FIFO Queues Are All You Need for Cache Eviction

**What I should say:**

Hey everyone, I'm Lavneet. The paper I picked is called FIFO Queues Are All You
Need for Cache Eviction. It came out at SOSP in 2023, from a group at Carnegie
Mellon and Emory.

The title is kind of a bold claim, and that's actually why I picked it. What I
did for this project was take their experiments and run them again myself on
two of their datasets, to see if I'd get the same results they did.

**Transition:**

Before I get into what they built, let me explain where this problem actually
shows up.

## Slide 2: Where the eviction algorithm sits

**What I should say:**

So basically, a cache sits in between a client and a backend. The backend is
where all your data actually lives, like a database. The cache is a small, fast
copy of the stuff people ask for most.

The thing is, it's small. It might only hold around one percent of your data.

So when a request comes in, two things can happen. If what you want is already
in the cache, that's a hit, and you get it back in microseconds. If it's not
there, that's a miss, and now you have to go all the way to the backend. That's
slower, and you're also putting load on the exact thing the cache was supposed
to protect.

So the number everyone cares about is the miss ratio, which is just misses
divided by total requests.

And here's where it gets interesting. The cache fills up almost immediately and
then it stays full. So every single time you want to put something new in, you
have to throw something else out. The rule that decides what gets thrown out is
the eviction algorithm, and that's basically the only control you have over
your miss ratio. For a company running this at scale, one percent better can
mean a lot fewer servers.

**Transition:**

So the obvious question is, what rule do people actually use? That's where the
problem starts.

## Slide 3: Efficiency bought with complexity

**What I should say:**

For about thirty years the answer has been LRU, or something built on top of
LRU. LRU means least recently used, so you throw out whatever hasn't been
touched in the longest time.

And people have built a lot of smarter versions of it. ARC, 2Q, LIRS, TinyLFU,
and a bunch more. They all work by keeping objects in an LRU queue and adding
extra bookkeeping on top.

They do get you a better miss ratio. But they cost you three things.

First, memory. An LRU queue is usually a linked list, so every object has to
carry two pointers around with it. If the objects you're caching are small,
which is really common, those pointers eat a real chunk of your cache.

Second, throughput. With LRU, every time you read something you have to move it
to the front of the queue. That's a write, and if multiple threads are doing it
you need a lock. So you're taking a lock on a cache hit, which is supposed to
be the fast path.

Third, complexity. These are hard to tune and hard to implement correctly. The
authors point out that LIRS implementations that got published in other papers
actually had two bugs in them.

What this means is a lot of real systems just don't use any of these. They run
plain FIFO or plain LRU and accept a worse miss ratio, because the better
algorithm is too much hassle to deploy.

**Transition:**

So that's the setup. Here's the observation this paper is built on.

## Slide 4: The key observation, 72%

**What I should say:**

There's a term called a one-hit wonder. It just means an object that gets
requested once and then never again.

If you look at a whole trace, start to finish, about 26 percent of objects are
one-hit wonders. That doesn't sound like a big deal.

But the authors point out that's the wrong way to measure it. A cache never
sees a whole trace. It only sees a window of requests roughly the size of
itself, because anything older than that has already been evicted.

So they measured it again over a window holding about ten percent of the
objects, which is much closer to what a real cache sees. And in that window, 72
percent of the objects were requested exactly once.

What that means is most of what you're putting into your cache is never going
to be asked for again. And that kind of changes the whole job. It's less about
carefully working out which object is the most valuable one to keep, and more
about getting the useless stuff out fast, before it takes up space something
useful could have used.

**Transition:**

And that's exactly what their algorithm does.

## Slide 5: Ask a cheaper question first

**What I should say:**

The idea here is a change in what question you're asking.

Every LRU variant is trying to answer: out of everything in my cache, which
object is the least valuable? And to answer that you have to keep a ranking up
to date, which is where all the cost comes from.

S3-FIFO asks a cheaper question first. It just asks, has this object been
requested even once since I let it in?

That's a much easier question to answer. You can do it with a two-bit counter
instead of two pointers. And when there's a cache hit, you just add one to that
counter. Nothing moves, nothing gets reordered, so you don't need a lock.

The table here is the side by side. Two pointers versus two bits. A locked
reorder on every hit versus just bumping a counter. LRU queues versus only FIFO
queues.

And the surprising part, at least to me, is the direction this goes. You'd
expect dropping LRU to make your miss ratio worse, since that's the whole
reason people use LRU in the first place. It actually makes it better.

**Transition:**

So let me walk through how it works.

## Slide 6: Three FIFO queues

**What I should say:**

The way this works is there are three FIFO queues. FIFO just means first in,
first out, like a normal line.

S is the small one. It's ten percent of the cache. You can think of it as
probation, it's where new objects land.

M is the main one, the other ninety percent. That's where objects live once
they've proven themselves.

And G is a ghost queue. It only stores keys, not the actual data, so it's
really cheap to keep around.

So here's the flow. A new object comes in and goes into S. When S fills up, the
object at the end of the line has to go, and there's two cases. If that object
got requested at least once while it was sitting in S, it's shown it's worth
something, so it moves over to M. If it never got requested, which is what
usually happens, we throw the data away but we hang onto its key in G.

And this is the part I think is clever. If that same key shows up again later,
we check G and we see we've thrown this exact thing out before. So now we know
it isn't really a one-hit wonder. So this time it skips probation completely
and goes straight into M.

M itself works kind of like a clock. When it needs space it looks at the oldest
object, and if that object's counter is above zero, it puts it back at the
front and knocks the counter down by one. If the counter is already at zero,
that object gets evicted.

The code on the right is the whole algorithm. That's my own summary of it, in
four lines. The actual pseudocode in the paper is about forty lines, because it
spells out each of the functions separately. Either way it fits on one slide,
which is sort of the point.

And the thing to notice is nothing ever moves just because you read it. That's
where all the speed comes from.

**Transition:**

So that's the paper. Let me talk about what I actually ran.

## Slide 7: Two datasets, every trace

**What I should say:**

In the paper they test on 6594 traces across fourteen different datasets.
That's several terabytes, so there was no way I was running all of it on a
laptop.

So what I did instead was pick the two datasets that would actually fit, MSR
and CloudPhysics, and run those completely. Every single trace, not a sample.
You can see that in the table, 14 traces and 106 traces, both marked complete.

That came out to 120 traces and about 2.52 billion requests, across twelve
different algorithms, at two different cache sizes. It took about twenty hours
to run.

One thing I want to be clear about, the algorithm implementations aren't mine.
Those are the authors' own code, through their simulator. What I wrote is
everything around it, the harness that loads the traces and runs the
experiments.

And there's one more thing on this slide that matters a lot for later. Look at
the type column. Both of the datasets I could run are block storage workloads.
The paper's data is mostly web traffic and key-value stores, and those are way
more skewed, meaning a small number of objects get requested a ton. Skew is
exactly what this algorithm takes advantage of. So basically, I'm testing it on
the kind of workload that suits it the least.

**Transition:**

Before I trusted any of my results, I wanted to be sure I actually understood
the algorithm.

## Slide 8: The paper contradicts itself twice

**What I should say:**

So I implemented S3-FIFO myself, by hand, straight from the pseudocode in the
paper. And doing that, I found the paper disagrees with itself in two places.

The first one is about when an object gets promoted from S to M. The written
text in section 4.1 says it's promoted if it was accessed more than once. But
the pseudocode on line 23 says the counter has to be greater than one. Those
sound like the same thing but they're not, because the counter starts at zero,
so there's an off-by-one between them.

The second one is about whether that counter gets reset when the object gets
promoted. The text says it does. The pseudocode doesn't mention it at all.

So instead of guessing which one was right, I built all four combinations and
tested each one against the authors' actual C++ code on the same trace.

That's what this table shows. The top row, the highlighted one, is the version
that matched, and the gap was 0.0014, which is tiny. And what's interesting is
that version takes the threshold from the pseudocode and the counter reset from
the written text. So neither half of the paper is right on its own. If you only
read one of them, you end up implementing a slightly different algorithm.

**Transition:**

Alright, so onto the actual results. There's four of them.

## Slide 9: Result 1, one-hit wonders

**What I should say:**

The first one is the one-hit wonder measurement, and I started here on purpose,
because it needs no cache simulation at all. You're literally just counting how
many objects show up once. So if I got this wrong, nothing after it would be
worth anything.

The chart on top is theirs, from the paper. The one underneath is mine.

What you're looking at in both is the one-hit wonder ratio going down as the
window gets bigger, which is the trend I was talking about earlier.

The thing I'd point at are the blue stars on my charts. Those aren't my data.
Those are the numbers the paper published in their Table 1, and I just dropped
them on top of my results to compare. And they land basically right on my
averages, at all three window sizes, on both datasets. The worst disagreement
anywhere is 0.04.

There's one more check I did. My MSR traces add up to 409.8 million requests,
and the paper reports 410 million. So I'm pretty confident I'm working with the
same data they were.

**Transition:**

So the setup checks out. Now the main result.

## Slide 10: Result 2, miss ratio reduction

**What I should say:**

This is the big one.

Quick note on how it's measured. You can't just average raw miss ratios across
traces, because some traces have a 5 percent miss ratio and some have 60, so
the average doesn't mean anything. So instead, for every trace, you compare
each algorithm against plain FIFO on that same trace, and you report the
improvement.

Look at the left panels, that's the large cache size. S3-FIFO comes out first
out of eleven algorithms. My average improvement over FIFO was 14.8 percent,
and the paper says 14. So that's about as close as a reproduction is going to
get.

There's a second thing on here worth looking at. Find the P10 bars, that's the
worst tenth of traces, so basically the bad cases. S3-FIFO stays positive
there. But TinyLFU and LIRS both go negative. Negative means on those traces
they're doing worse than if you'd just used plain FIFO and not been clever at
all.

What that tells you is S3-FIFO is never much worse than the baseline. And for
someone running this in production, that kind of reliability probably matters
more than being slightly better on average.

Now on the right panels, the small cache size, my ranking came out different
from theirs. I'll come back to why in a couple of slides.

**Transition:**

First it helps to break this down by dataset.

## Slide 11: Result 3, per dataset

**What I should say:**

This one is useful because the paper reports MSR and CloudPhysics as their own
separate rows. So I can compare my two datasets against their exact numbers for
those same datasets, instead of comparing against an average that includes a
bunch of workloads I never ran.

And what my chart shows is the win is basically coming from CloudPhysics. On
MSR by itself, ARC actually comes out slightly ahead, 0.132 against 0.131.
That's close enough that I wouldn't call it a real difference. But on
CloudPhysics, S3-FIFO is clearly ahead, 0.151 against 0.110.

And if you go look at the paper's rows for those same two datasets, you see the
same pattern. The block storage datasets are where S3-FIFO's lead is smallest.
So my results and theirs actually agree here, which was reassuring.

**Transition:**

The last result is about the one setting this algorithm has.

## Slide 12: Result 4, how big should S be

**What I should say:**

S3-FIFO basically has one tunable parameter, which is how big to make that
small queue S. The authors set it at ten percent.

So I swept it, meaning I ran it at a bunch of different sizes to see what
happened. And my best result was five percent on the large cache and
twenty-five percent on the small cache. Not ten.

So at first I wrote this down as a disagreement. But then I reread what they
actually claim in section 6.2. They never say ten percent is the best value.
What they say is that the algorithm isn't very sensitive to this setting.

Now, my line clearly drops off, and it looks like it drops off way harder than
theirs. A lot of that is just the axis. Their y-axis goes from zero up to 0.4,
because they're plotting the whole spread from P10 to P90. Mine is plotting
only the mean, so it's zoomed right in and the same change fills the frame. If
you look at their orange mean markers, they come down too.

The shape is the same in both. It holds up while the small queue stays small,
then falls off once the queue gets big. On my large cache, anywhere from one
percent to ten percent is within about four percent of my best. Push it up to
half the cache and you lose about a third of the benefit.

So ten percent is a safe choice and my data supports that. I'd push back a
little on the word insensitive though, because by the time you're at fifty
percent it definitely is sensitive.

That was probably the biggest thing I learned doing this project. Check what
the paper actually says before you decide you've found a problem with it.

**Transition:**

So let me pull the differences together, because they're all connected.

## Slide 13: Three gaps, one cause

**What I should say:**

There were three places where my numbers didn't match theirs.

One, 2Q beat S3-FIFO at the small cache size, where the paper had S3-FIFO
first. Two, my absolute improvements were smaller than theirs across the board.
And three, I ended up with 14 MSR traces where the paper says 13, although our
total request counts match, so that one's probably just a counting difference
on their end.

The first two come from the same thing, and it's what I flagged earlier. The
only two datasets small enough for me to run are both block storage, which
means less skew, which means less for this algorithm to take advantage of.

And for the small cache specifically, if your cache is tiny, objects get pushed
out really fast, sometimes before they ever get a chance to be requested a
second time and prove they're worth keeping. 2Q doesn't have that problem as
much, because it reserves a fixed chunk of space for new objects. S3-FIFO
doesn't do that.

The way I'd put it is this isn't a failed reproduction. It's a reproduction on
the two datasets out of fourteen that suit this algorithm the least. If I'd
been able to run the CDN traces, my numbers would have looked better and
honestly proven less.

**Transition:**

So, does the paper hold up?

## Slide 14: The central claim holds

**What I should say:**

Yeah, mostly.

The main claim reproduced. At the large cache size S3-FIFO came out first of
eleven algorithms, and my 14.8 percent lines up with their 14. And all six of
the one-hit wonder values from their Table 1 reproduced within 0.04.

It's qualified in one spot, at the very small cache size on block workloads,
where it came second instead of first. But their own per-dataset figure kind of
predicts that, so I'd call that a limit on what I was able to test.

And then the last line there, two things I found that you wouldn't get just
from reading the paper. The two places it contradicts itself, which I showed
earlier. And their public trace files number things starting from zero in one
dataset and starting from one in the other, which would quietly break your
analysis if you assumed they were the same.

So, forty lines of FIFO queues beating thirty years of LRU variants, measured
on the workloads that suit them the least.

That's it. Happy to take any questions.

## If you need it shorter

To get to about 10 minutes, cut these and nothing else:

- Slide 3, drop the LIRS bugs line
- Slide 10, drop the whole P10 bars paragraph
- Slide 11, cut to just the two number comparisons
- Slide 12, drop the "biggest thing I learned" line

Keep slide 8 whole. The two contradictions are the most interesting thing you
found and the most likely thing to get asked about.
