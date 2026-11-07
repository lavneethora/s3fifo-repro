"""Build the talk as a single standalone HTML file.

Follows the frontend-slides skill (github.com/zarazhangrui/frontend-slides, MIT):
its mandatory fixed-stage CSS, authored at 1920x1080 and scaled to the window,
with the Swiss Modern preset (Archivo 800 + Nunito, white/black/red #ff3300,
visible grid, asymmetric layouts).

Images are base64-inlined so the result is one portable file.

  python slides/build_slides.py        ->  slides/index.html
"""

import base64
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")
PAPER = os.path.join(ROOT, "report", "paper_figures")
OUT = os.path.join(ROOT, "slides", "index.html")

DECK_LABEL = "S3-FIFO · Yang et al., SOSP '23"


# Figures are sized by height so each one fills as much of the slide as its own
# aspect ratio allows. Forcing width:100% on a short box would letterbox the
# wide plots down to a narrow strip.
FIG_STYLE = "height:286px;width:auto;max-width:100%;object-fit:contain"


def img(path, alt, style=""):
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="{style}">'


def fig_pair(n, title, lede, paper_file, ours_file, paper_cap, ours_cap, notes):
    """A results slide: the paper's figure above ours."""
    return {
        "id": f"fig{n}",
        "html": f"""
<div class="head">
  <h2>{title}</h2>
  <p class="lede">{lede}</p>
</div>
<div class="pair">
  <div class="shot">
    <p class="shot-label">Original <span class="src">paper</span></p>
    {img(os.path.join(PAPER, paper_file), paper_cap, FIG_STYLE)}
  </div>
  <div class="shot">
    <p class="shot-label accent">Reproduced <span class="src">ours</span></p>
    {img(os.path.join(FIG, ours_file), ours_cap, FIG_STYLE)}
  </div>
</div>""",
        "notes": notes,
    }


SLIDES = [
    {
        "id": "cover",
        "cls": "cover",
        "chrome": False,
        "html": """
<div class="cover-grid">
  <div class="cover-rule"></div>
  <p class="kicker">Paper reproduction</p>
  <h1>FIFO Queues<br>Are All You Need<br>for Cache Eviction</h1>
  <div class="cover-meta">
    <div>
      <p class="meta-k">Authors</p>
      <p class="meta-v">Yang · Zhang · Qiu · Yue · Rashmi</p>
      <p class="meta-v dim">CMU, Emory, Pelikan Foundation. SOSP '23</p>
    </div>
    <div>
      <p class="meta-k">Reproduced by</p>
      <p class="meta-v">Lavneet Hora</p>
      <p class="meta-v dim">120 traces · 2.52B requests</p>
    </div>
  </div>
</div>""",
        "notes": "This is a reproduction of a 2023 SOSP paper on cache eviction. The title is deliberately provocative: for thirty years the field has assumed you need LRU plus something clever on top. I re-ran their experiments on two of their datasets, completely, and I will show you where it held up and where it did not.",
    },
    {
        "id": "background",
        "html": """
<div class="head"><h2>Where the eviction algorithm sits</h2></div>
<div class="flowrow">
  <div class="node">Client</div>
  <div class="arrow"></div>
  <div class="node solid">Cache<span>holds maybe 1% of the data</span></div>
  <div class="arrow dash"></div>
  <div class="node">Backend</div>
</div>
<div class="twocol">
  <div><p class="tag">Hit</p><p class="body">Served from memory, microseconds, backend never touched.</p></div>
  <div><p class="tag accent">Miss</p><p class="body">Full round trip, plus load the backend has to absorb.</p></div>
</div>
<p class="mono big-mono">miss ratio = misses / requests</p>
<p class="body wide">The cache is always full, so every admission forces an eviction. Which object gets discarded is the only real lever on that ratio, and at scale one point of it is worth a lot of hardware.</p>""",
        "notes": "Grounding, keep it short. A cache holds a small slice of the data. A hit is microseconds; a miss is a full round trip plus extra load on the backend you were trying to protect. Because the cache is always full, admitting anything means discarding something, and the rule that picks the victim is the only real control you have over the miss ratio.",
    },
    {
        "id": "problem",
        "html": """
<div class="head"><h2>Efficiency bought with complexity</h2></div>
<div class="split">
  <div class="split-l">
    <p class="body">Three decades of work on eviction, and essentially all of it builds on an LRU queue:</p>
    <p class="mono list">ARC · 2Q · SLRU · LIRS<br>TinyLFU · LeCaR · CACHEUS · LHD</p>
  </div>
  <div class="split-r">
    <div class="defn"><p class="dt accent">Memory</p><p class="dd">Two pointers per object, on objects that are often tiny</p></div>
    <div class="defn"><p class="dt accent">Throughput</p><p class="dd">A hit reorders the queue, so it takes a lock on the hot path</p></div>
    <div class="defn"><p class="dt accent">Complexity</p><p class="dd">Parameters that resist tuning, and published LIRS code with two real bugs</p></div>
  </div>
</div>
<p class="body wide">So production systems keep running plain FIFO or LRU and absorb the worse miss ratio. The better algorithm never ships.</p>""",
        "notes": "The setup for the whole paper. Over three decades people built smarter eviction algorithms and essentially all sit on LRU queues. That buys efficiency and costs memory, throughput and simplicity. The authors note that LIRS implementations in prior published work contained two separate bugs. The practical result is the last line: engineers do not deploy these, they run FIFO or LRU and eat the difference.",
    },
    {
        "id": "observation",
        "cls": "invert",
        "html": """
<div class="head"><p class="kicker accent">The key observation</p></div>
<div class="statrow">
  <p class="huge">72<span class="pct">%</span></p>
  <p class="stat-body">of objects are requested <em>exactly once</em> within a window holding 10% of a trace's objects</p>
</div>
<p class="body wide dim">Measured across 6594 production traces. Over a whole trace the figure is 26%, but a cache never sees a whole trace: it sees a window about the size of itself. Most of what you admit is never asked for again.</p>""",
        "notes": "This is the insight the algorithm falls out of, so spend a moment. People have long measured what fraction of objects are requested only once, and across whole traces it is about a quarter. The authors point out that is the wrong measurement, because a cache never sees the whole trace. Over a window holding ten percent of the objects, 72 percent are one-hit wonders. So most of what you admit is garbage, and the job is to get rid of it fast. They call that quick demotion.",
    },
    {
        "id": "novelty",
        "html": """
<div class="head">
  <h2>Ask a cheaper question first</h2>
  <p class="lede">Every LRU variant asks which object is <em>least valuable</em>. S3-FIFO asks whether an object has proved itself <em>at all</em>, which costs two bits.</p>
</div>
<table class="t">
  <tr><th></th><th>LRU and its variants</th><th class="accent">S3-FIFO</th></tr>
  <tr><td>Metadata per object</td><td>Two pointers</td><td class="accent">Two bits</td></tr>
  <tr><td>On a cache hit</td><td>Move to head, take a lock</td><td class="accent">Increment a counter, no lock</td></tr>
  <tr><td>Ordering structure</td><td>One or more LRU queues</td><td class="accent">FIFO queues only</td></tr>
  <tr><td>Tunable parameters</td><td>Several, workload-specific</td><td class="accent">One, and it barely matters</td></tr>
</table>
<p class="body wide">The surprise is the direction. Giving up LRU is supposed to cost efficiency. It buys it.</p>""",
        "notes": "Frame it as a question rather than a data structure, because that is what is new. Every other algorithm is trying to rank objects by value, which is expensive to maintain. S3-FIFO asks a cheaper question: has this been requested even once since we admitted it? Walk the table. Then the last line, which should be the surprising part: conventional wisdom says FIFO is what you settle for. Here it wins.",
    },
    {
        "id": "method",
        "html": """
<div class="head"><h2>Three FIFO queues</h2></div>
<div class="diagram">__DESIGN__</div>
<div class="code">
  <div class="cl"><span class="ck">on hit</span><span class="cv">freq = min(freq + 1, 3)</span></div>
  <div class="cl"><span class="ck">on insert</span><span class="cv">in G ? M : S</span></div>
  <div class="cl"><span class="ck">S full</span><span class="cv">freq &gt; 1 ? M : G</span></div>
  <div class="cl"><span class="ck">M full</span><span class="cv">freq &gt; 0 ? reinsert, freq-- : evict</span></div>
</div>
<p class="body wide">That is the entire algorithm. No object is ever moved because it was read, which is why a hit needs no lock.</p>""",
        "notes": "Walk the diagram left to right, then the code. A new object goes into S, a tenth of the cache. When S fills the tail leaves: promoted to M if it was requested, otherwise dropped with only its key kept in G. If that key turns up again we know it is not a one-hit wonder, so it goes straight to M and skips probation. M evicts like a clock sweep. The four lines are genuinely all of it. Nothing moves on a read, which is where the scalability comes from.",
    },
    {
        "id": "setup",
        "html": """
<div class="head"><h2>Two datasets, every trace</h2></div>
<table class="t">
  <tr><th>Dataset</th><th class="r">Traces</th><th class="r">Requests</th><th>Type</th><th>Coverage</th></tr>
  <tr><td>MSR Cambridge 2007</td><td class="r">14</td><td class="r">410M</td><td>Block</td><td class="accent">Complete</td></tr>
  <tr><td>CloudPhysics 2015</td><td class="r">106</td><td class="r">2,114M</td><td>Block</td><td class="accent">Complete</td></tr>
  <tr><td>Paper's full set</td><td class="r">6,594</td><td class="r">247,017M</td><td>Mostly web, KV</td><td class="dim">Several TB</td></tr>
</table>
<div class="split">
  <div class="split-l">
    <p class="tag">12 algorithms, 2 cache sizes</p>
    <p class="mono list sm">FIFO LRU CLOCK ARC 2Q SLRU<br>LIRS TinyLFU LeCaR LHD CACHEUS S3-FIFO</p>
    <p class="body sm">Cache at 10% and 0.1% of each trace's object count, object size ignored, as in the paper.</p>
  </div>
  <div class="split-r centered">
    <p class="bignum">2.52B</p>
    <p class="body sm">requests replayed with the authors' own libCacheSim, about 20 hours on a laptop</p>
  </div>
</div>
<p class="body wide">Both datasets I could run are <strong>block</strong> workloads. The paper's evidence is mostly web and key-value, which are far more skewed. Remember that when the numbers diverge.</p>""",
        "notes": "Be upfront about scope. The paper runs 6594 traces across fourteen datasets, several terabytes, which a laptop cannot do. I took the two that fit and ran them completely, every trace, not a sample. The algorithms are the authors' own through libCacheSim, so what I wrote is the harness. Land hard on the last line, because it explains every disagreement later: both my datasets are block storage, and block traces are much less skewed than the web traces that dominate the paper. Skew is what this algorithm exploits.",
    },
    {
        "id": "validation",
        "html": """
<div class="head">
  <h2>The paper contradicts itself twice</h2>
  <p class="lede">Section 4.1 says promote when an object was "accessed more than once"; pseudocode line 23 says the counter must exceed one. The prose clears the counter on promotion; the pseudocode never mentions it. So I built all four readings and measured each against the authors' C++.</p>
</div>
<table class="t">
  <tr><th>Promotion rule</th><th>Reset counter</th><th class="r">Worst gap</th><th>Described in</th></tr>
  <tr class="hit"><td>freq &gt; 1</td><td>Yes</td><td class="r accent">0.0014</td><td class="accent">Neither alone</td></tr>
  <tr><td>freq &gt; 0</td><td>Yes</td><td class="r">0.0017</td><td>The prose</td></tr>
  <tr><td>freq &gt; 0</td><td>No</td><td class="r">0.0055</td><td>Neither</td></tr>
  <tr><td>freq &gt; 1</td><td>No</td><td class="r">0.0058</td><td>The pseudocode</td></tr>
</table>
<p class="body wide">The match takes its threshold from the <strong>pseudocode</strong> and its counter reset from the <strong>prose</strong>. Neither half of the paper is right on its own.</p>""",
        "notes": "This is what I would lead with if asked what I learned. Two details differ between the prose and the pseudocode, and rather than guess I implemented all four combinations and measured each against the authors' own C++ on the same trace. The highlighted row matches to fourteen ten-thousandths of a miss ratio, and it takes one detail from each half of the paper. Anyone implementing from only the pseudocode, or only the prose, gets a measurably different algorithm.",
    },
]

SLIDES.append(fig_pair(
    1, "Result 1 · One-hit wonders",
    "All six of the paper's tabulated values reproduce within 0.04",
    "paper_fig3.png", "fig3_one_hit_wonder.png",
    "Paper Figure 3: one-hit-wonder ratio against sequence length across 6594 traces",
    "Our reproduction on MSR and CloudPhysics, with the paper's published values marked as stars",
    "This needs no cache simulation at all, just counting, so it validates the trace decoding before anything else depends on it. The blue stars on my panels are the paper's own published numbers, and they sit on my means at all three sequence lengths for both datasets. My MSR traces also total 409.8 million requests against their stated 410 million, so I am confident it is the same data.",
))
SLIDES.append(fig_pair(
    2, "Result 2 · Miss ratio reduction",
    "First of eleven on the large cache. Paper's mean 14%, ours 14.8%",
    "paper_fig6.png", "fig6_miss_ratio_reduction.png",
    "Paper Figure 6: percentiles of miss ratio reduction from FIFO, per algorithm",
    "Our reproduction of the same percentiles over 120 traces",
    "The headline. On the large cache size S3-FIFO is first of eleven algorithms and my mean reduction over FIFO is 14.8 percent against the 14 percent stated in their text. Point at the P10 bars too: S3-FIFO stays positive while TinyLFU and LIRS go negative, meaning on the worst tenth of traces those are beaten by plain FIFO. On the small cache my ordering differs, and the next slides explain why.",
))
SLIDES.append(fig_pair(
    3, "Result 3 · Per dataset",
    "The paper breaks out MSR and CloudPhysics as their own rows, so we can compare directly",
    "paper_fig7.png", "fig7_per_dataset.png",
    "Paper Figure 7: mean reduction per dataset, one row per dataset",
    "Our reproduction split by dataset at both cache sizes",
    "Useful because the paper publishes my two datasets as separate rows, so I can check them individually rather than against a pooled average. The win is carried by CloudPhysics: on MSR alone ARC very slightly beats S3-FIFO, 0.132 against 0.131, while on CloudPhysics S3-FIFO is well ahead, 0.151 against 0.110. The paper's own rows for those datasets show the same pattern.",
))
SLIDES.append(fig_pair(
    4, "Result 4 · How big should S be?",
    "The paper's claim is insensitivity, not that 10% is optimal",
    "paper_fig11.png", "fig11_small_queue.png",
    "Paper Figure 11: reduction across probationary queue sizes, mean nearly flat",
    "Our sweep on MSR, peaking near 5% at the large cache and 25% at the small",
    "I nearly reported this as a disagreement and then realised it is not one. My best setting is 5 percent on the large cache and 25 on the small, not the paper's 10, so at first glance they look wrong. But section 6.2 claims S3-FIFO is not sensitive to the size of S, and their own figure shows a nearly flat mean. They never claim 10 is the argmax. My curve is flat too and 10 is within half a point of the best at both sizes. Check what was claimed before calling something a failed reproduction.",
))

SLIDES.append({
    "id": "differences",
    "html": """
<div class="head"><h2>Three gaps, one cause</h2></div>
<table class="t">
  <tr><th>What differs</th><th>Why</th></tr>
  <tr><td class="accent">2Q wins at the small cache</td><td>Block traces are less skewed, so a tiny cache evicts objects before they prove reuse. 2Q reserves fixed space for new objects; S3-FIFO does not.</td></tr>
  <tr><td class="accent">Smaller absolute gains</td><td>Same cause. On the two datasets we share with the paper, its own Figure 7 shows the same narrow margins.</td></tr>
  <tr><td class="accent">14 MSR traces, not 13</td><td>The public dataset has 14 files that all clear the paper's 1M cutoff. Request totals still agree: 409.8M against their 410M.</td></tr>
</table>
<div class="split">
  <div class="split-l"><p class="kick-stmt">Not a failed reproduction. A reproduction on the two datasets of fourteen that suit the algorithm <strong>least</strong>.</p></div>
  <div class="split-r"><p class="body sm">Had I run the CDN or key-value traces instead, the margins would have been wider and the result less interesting.</p></div>
</div>""",
    "notes": "Be direct rather than defensive. Every difference traces back to one decision: only two datasets were small enough to run, and both are block storage. The paper's evidence is dominated by web and key-value traces, which are much more skewed, and skew is exactly where quick demotion pays. So I tested the algorithm on its worst ground. If I had picked the CDN traces the numbers would look better and prove less.",
})

SLIDES.append({
    "id": "conclusion",
    "cls": "invert",
    "html": """
<div class="head"><h2>The central claim holds</h2></div>
<div class="statrow tight">
  <p class="huge">14.8<span class="pct">%</span></p>
  <p class="stat-body">mean miss ratio reduction over FIFO at the large cache size, first of eleven algorithms. The paper reports 14%.</p>
</div>
<div class="defns">
  <div class="defn"><p class="dt accent">Reproduced</p><p class="dd dim">All six of Table 1's one-hit-wonder values within 0.04, on 120 traces and 2.52B requests</p></div>
  <div class="defn"><p class="dt accent">Qualified</p><p class="dd dim">Second at a 0.1% cache on block workloads, which the paper's own per-dataset figure predicts</p></div>
  <div class="defn"><p class="dt accent">Found in passing</p><p class="dd dim">Two prose-versus-pseudocode contradictions, and a 0 versus 1 indexing split in the public traces</p></div>
</div>
<p class="closer">Forty lines of FIFO beat thirty years of LRU variants, measured on the workloads that suit them least.</p>
<p class="cite mono">doi 10.1145/3600006.3613147 · github.com/lavneethora/s3fifo-repro</p>""",
    "notes": "Close on the big number: my mean is 14.8 and the paper's own text says 14. Then the three lines. Reproduced on every value I could check. Qualified at a tiny cache on block workloads, predicted by their own data, so a scope limit rather than a contradiction. And the reproduction turned up two places where the paper contradicts itself plus an indexing inconsistency in the public traces. Finish on the last line and take questions.",
})


def build():
    base_css = open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "viewport-base.css")).read()
    design = img(os.path.join(FIG, "design_s3fifo.png"),
                 "The three queues of S3-FIFO: a small probationary queue S, a main queue M, and a ghost queue G",
                 "width:100%;height:270px;object-fit:contain")

    parts = []
    for i, s in enumerate(SLIDES):
        cls = " " + s["cls"] if s.get("cls") else ""
        body = s["html"].replace("__DESIGN__", design)
        chrome = "" if s.get("chrome") is False else (
            f'<div class="chrome"><span>{DECK_LABEL}</span>'
            f'<span>{i + 1:02d} / {len(SLIDES):02d}</span></div>')
        notes = f'<div class="notes" hidden>{s["notes"]}</div>'
        parts.append(f'<section class="slide{cls}" id="{s["id"]}">{chrome}'
                     f'<div class="inner">{body}</div>{notes}</section>')

    html = TEMPLATE.replace("__BASE_CSS__", base_css).replace(
        "__SLIDES__", "\n".join(parts)).replace("__COUNT__", str(len(SLIDES)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(html)
    kb = os.path.getsize(OUT) / 1024
    print(f"  wrote {OUT} ({kb:.0f} KB, {len(SLIDES)} slides)")


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>S3-FIFO Reproduction</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=Nunito:wght@400;600;700&display=swap">
<style>
:root{
  --paper:#ffffff; --ink:#0a0a0a; --accent:#ff3300; --muted:#6b6b6b;
  --rule:#d6d6d6; --stage-bg:#141414; --slide-bg:#ffffff;
  --display:'Archivo',sans-serif; --body:'Nunito',sans-serif;
  --pad:104px;
}
__BASE_CSS__

/* ---------- Swiss Modern ---------- */
.slide{ background:var(--paper); color:var(--ink); font-family:var(--body); }
.slide .inner{
  position:absolute; inset:0; padding:var(--pad) var(--pad) 92px;
  display:flex; flex-direction:column; justify-content:space-between;
}
.slide.cover .inner{ padding:0; }

.chrome{
  position:absolute; left:var(--pad); right:var(--pad); top:52px;
  display:flex; justify-content:space-between; align-items:baseline;
  font-family:var(--display); font-weight:500; font-size:19px;
  letter-spacing:.14em; text-transform:uppercase; color:var(--muted);
  border-top:2px solid var(--ink); padding-top:14px;
}
.slide.invert{ background:var(--ink); color:var(--paper); }
.slide.invert .chrome{ border-top-color:var(--paper); color:#8f8f8f; }
.slide.invert .t th{ border-bottom-color:var(--paper); }
.slide.invert .t td{ border-bottom-color:#333; }
.slide.invert .dim{ color:#9a9a9a; }

h1{ font-family:var(--display); font-weight:800; font-size:108px; line-height:.98;
    letter-spacing:-.025em; margin:0; }
h2{ font-family:var(--display); font-weight:800; font-size:70px; line-height:1.02;
    letter-spacing:-.02em; margin:0; max-width:1500px; }
.head{ display:flex; flex-direction:column; gap:20px; }
.lede{ font-size:29px; line-height:1.4; color:var(--muted); max-width:1450px; margin:0; }
.slide.invert .lede{ color:#9a9a9a; }
.kicker{ font-family:var(--display); font-weight:700; font-size:21px; letter-spacing:.2em;
         text-transform:uppercase; color:var(--muted); margin:0; }
.kicker.accent{ color:var(--accent); }
.accent{ color:var(--accent); }
.dim{ color:var(--muted); }
.body{ font-size:30px; line-height:1.45; margin:0; }
.body.sm{ font-size:25px; }
.body.wide{ max-width:1560px; }
strong{ font-weight:700; }
em{ font-style:italic; }

/* cover */
.cover-grid{ position:absolute; inset:0; padding:var(--pad);
             display:flex; flex-direction:column; justify-content:center; gap:46px; }
.cover-rule{ position:absolute; left:var(--pad); right:var(--pad); top:150px;
             height:10px; background:var(--accent); }
.cover-meta{ display:flex; gap:120px; border-top:2px solid var(--ink); padding-top:30px; }
.meta-k{ font-family:var(--display); font-weight:700; font-size:18px; letter-spacing:.18em;
         text-transform:uppercase; color:var(--accent); margin:0 0 10px; }
.meta-v{ font-size:27px; margin:0; line-height:1.35; }
.meta-v.dim{ font-size:23px; color:var(--muted); }

/* flow diagram */
.flowrow{ display:flex; align-items:center; gap:0; }
.node{ font-family:var(--display); font-weight:700; font-size:30px; padding:30px 44px;
       border:3px solid var(--ink); display:flex; flex-direction:column; gap:7px; }
.node span{ font-family:var(--body); font-weight:400; font-size:21px; color:var(--muted); }
.node.solid{ background:var(--ink); color:var(--paper); border-color:var(--ink); }
.node.solid span{ color:#b5b5b5; }
.arrow{ flex:1; height:3px; background:var(--ink); position:relative; }
.arrow.dash{ background:repeating-linear-gradient(90deg,var(--ink) 0 14px,transparent 14px 26px); }
.arrow::after{ content:""; position:absolute; right:0; top:-7px;
               border-left:16px solid var(--ink); border-top:8px solid transparent;
               border-bottom:8px solid transparent; }

.twocol{ display:flex; gap:80px; }
.twocol>div{ flex:1; border-top:2px solid var(--rule); padding-top:18px; }
.tag{ font-family:var(--display); font-weight:700; font-size:22px; letter-spacing:.14em;
      text-transform:uppercase; margin:0 0 10px; }
.big-mono{ font-family:var(--display); font-weight:500; font-size:36px; letter-spacing:.02em; }
.mono{ font-family:var(--display); font-weight:500; letter-spacing:.02em; }
.mono.list{ font-size:30px; line-height:1.85; margin:0; }
.mono.list.sm{ font-size:23px; line-height:1.7; }

/* split */
.split{ display:flex; gap:86px; align-items:flex-start; }
.split-l{ width:46%; display:flex; flex-direction:column; gap:16px; }
.split-r{ flex:1; display:flex; flex-direction:column; gap:22px; }
.split-r.centered{ justify-content:center; gap:8px; }
.defns{ display:flex; flex-direction:column; gap:22px; }
.defn{ display:flex; gap:34px; align-items:baseline; border-top:2px solid var(--rule); padding-top:16px; }
.slide.invert .defn{ border-top-color:#333; }
.dt{ font-family:var(--display); font-weight:700; font-size:25px; width:280px; margin:0;
     letter-spacing:.02em; }
.dd{ flex:1; font-size:26px; line-height:1.4; margin:0; }
.bignum{ font-family:var(--display); font-weight:800; font-size:92px; line-height:1;
         color:var(--accent); margin:0; letter-spacing:-.02em; }

/* stat */
.statrow{ display:flex; align-items:center; gap:72px; }
.statrow.tight{ align-items:flex-end; gap:56px; }
.huge{ font-family:var(--display); font-weight:800; font-size:208px; line-height:.86;
       color:var(--accent); margin:0; letter-spacing:-.04em; white-space:nowrap; }
.huge .pct{ font-size:110px; }
.stat-body{ font-size:40px; line-height:1.3; margin:0; }
.closer{ font-size:38px; line-height:1.35; margin:0; max-width:1560px;
         border-top:4px solid var(--accent); padding-top:24px; }
.cite{ font-size:20px; color:#8f8f8f; margin:0; letter-spacing:.09em; }

/* table */
.t{ width:100%; border-collapse:collapse; font-size:26px; }
.t th{ font-family:var(--display); font-weight:700; font-size:21px; letter-spacing:.13em;
       text-transform:uppercase; text-align:left; padding:0 22px 14px 0;
       border-bottom:3px solid var(--ink); color:var(--ink); }
.slide.invert .t th{ color:var(--paper); }
.t td{ padding:17px 22px 17px 0; border-bottom:1px solid var(--rule);
       vertical-align:top; line-height:1.35; }
.t .r{ text-align:right; padding-right:34px; }
.t tr.hit td{ background:#fff3f0; font-weight:700; }

/* code */
.code{ background:var(--ink); padding:30px 38px; display:flex; flex-direction:column; gap:11px; }
.cl{ display:flex; gap:26px; font-family:var(--display); font-weight:500; font-size:25px; }
.ck{ width:170px; color:var(--accent); letter-spacing:.06em; }
.cv{ color:#f2f2f2; }
.diagram{ display:flex; justify-content:center; }

/* figure pairs */
.pair{ display:flex; flex-direction:column; gap:20px; }
.shot{ display:flex; flex-direction:column; gap:8px; align-items:flex-start; }
.shot-label{ font-family:var(--display); font-weight:700; font-size:20px; letter-spacing:.15em;
             text-transform:uppercase; margin:0; border-bottom:2px solid var(--rule);
             padding-bottom:7px; display:flex; gap:12px; align-items:baseline; }
.shot-label .src{ font-family:var(--body); font-weight:400; font-size:19px;
                  letter-spacing:0; text-transform:none; color:var(--muted); }
.shot img{ display:block; }
.kick-stmt{ font-size:33px; line-height:1.35; margin:0; border-left:8px solid var(--accent);
            padding-left:28px; }

.notes{ display:none; }
body.show-notes .notes{
  display:block; position:fixed; left:0; right:0; bottom:0; z-index:2000;
  background:rgba(10,10,10,.94); color:#f2f2f2; font-family:var(--body);
  font-size:17px; line-height:1.5; padding:18px 26px; max-height:34vh; overflow:auto;
}
body.show-notes .slide:not(.active) .notes{ display:none; }
.deck-controls{ font-family:var(--body); font-size:13px; color:#999;
                background:rgba(0,0,0,.55); padding:6px 14px; border-radius:20px; }
@media print{ .notes{ display:none !important; } }
</style>
</head>
<body>
<div class="deck-viewport">
  <div class="deck-stage" id="stage">
__SLIDES__
  </div>
</div>
<div class="deck-controls" id="ctl">1 / __COUNT__ &nbsp;·&nbsp; arrows to move &nbsp;·&nbsp; N for notes</div>
<script>
(function(){
  const slides=[...document.querySelectorAll('.slide')];
  const stage=document.getElementById('stage');
  const ctl=document.getElementById('ctl');
  let i=0;
  function scale(){
    const f=Math.min(window.innerWidth/1920, window.innerHeight/1080);
    const x=(window.innerWidth-1920*f)/2, y=(window.innerHeight-1080*f)/2;
    stage.style.transform='translate('+x+'px,'+y+'px) scale('+f+')';
  }
  function show(n){
    i=Math.max(0,Math.min(slides.length-1,n));
    slides.forEach((s,k)=>s.classList.toggle('active',k===i));
    ctl.firstChild.nodeValue=(i+1)+' / '+slides.length+' ';
    location.hash='#'+(i+1);
  }
  addEventListener('resize',scale);
  addEventListener('keydown',e=>{
    if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();show(i+1);}
    else if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();show(i-1);}
    else if(e.key==='Home'){show(0);} else if(e.key==='End'){show(slides.length-1);}
    else if(e.key==='n'||e.key==='N'){document.body.classList.toggle('show-notes');}
  });
  let sx=null;
  addEventListener('touchstart',e=>sx=e.touches[0].clientX,{passive:true});
  addEventListener('touchend',e=>{
    if(sx===null)return; const d=e.changedTouches[0].clientX-sx;
    if(Math.abs(d)>50) show(i+(d<0?1:-1)); sx=null;
  },{passive:true});
  addEventListener('hashchange',()=>{
    const n=parseInt((location.hash||'#1').slice(1),10);
    if(!isNaN(n)&&n-1!==i) show(n-1);
  });
  scale();
  const start=parseInt((location.hash||'#1').slice(1),10);
  show(isNaN(start)?0:start-1);
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
