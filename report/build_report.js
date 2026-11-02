// Builds the project report as a .docx, following the structure of the
// course-provided Report Template.docx: 16pt centred title, 14pt section
// headings, 12pt Calibri body, US Letter.
//
//   node report/build_report.js
//
// Paper figures must be extracted first:
//   python report/extract_paper_figures.py <paper.pdf>

const fs = require("fs");
const path = require("path");
const {
  AlignmentType, Document, ImageRun, Packer, Paragraph, ShadingType,
  Table, TableCell, TableRow, TextRun, WidthType,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const FIG = path.join(ROOT, "figures");
const PAPER = path.join(__dirname, "paper_figures");
const OUT = path.join(__dirname, "S3-FIFO_Reproduction_Report.docx");

const FONT = "Calibri";
const BODY_PT = 24;      // half-points, so 12pt
const HEAD_PT = 28;      // 14pt
const TITLE_PT = 32;     // 16pt
const CAPTION_PT = 20;   // 10pt
const CONTENT_PX = 624;  // 6.5in of content width at 96dpi

function title(text, bold) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [new TextRun({ text, font: FONT, size: TITLE_PT, bold: !!bold })],
  });
}

function heading(text) {
  return new Paragraph({
    spacing: { before: 320, after: 140 },
    children: [new TextRun({ text, font: FONT, size: HEAD_PT, bold: true })],
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.tight ? 80 : 180, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    children: [new TextRun({ text, font: FONT, size: BODY_PT })],
  });
}

function bullet(text) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 90, line: 276 },
    children: [new TextRun({ text, font: FONT, size: BODY_PT })],
  });
}

// A PNG stores its dimensions in the IHDR chunk: width and height are
// big-endian uint32s at byte offsets 16 and 20. Reading them here avoids
// shelling out just to measure an image.
function pngSize(buffer) {
  return [buffer.readUInt32BE(16), buffer.readUInt32BE(20)];
}

function figure(file, caption) {
  const data = fs.readFileSync(file);
  const [w, h] = pngSize(data);
  const width = CONTENT_PX;
  const height = Math.round((CONTENT_PX * h) / w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 60 },
      children: [new ImageRun({
        type: "png",
        data,
        transformation: { width, height },
      })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 220 },
      children: [new TextRun({ text: caption, font: FONT, size: CAPTION_PT, italics: true })],
    }),
  ];
}

function cell(text, { bold, width, align, shaded } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: shaded ? { type: ShadingType.CLEAR, fill: "EDF1F5" } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    children: [new Paragraph({
      alignment: align || AlignmentType.LEFT,
      children: [new TextRun({ text, font: FONT, size: 22, bold: !!bold })],
    })],
  });
}

function table(widths, rows) {
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: rows.map((cells, r) => new TableRow({
      children: cells.map((c, i) => cell(String(c), {
        bold: r === 0,
        shaded: r === 0,
        width: widths[i],
        align: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT,
      })),
    })),
  });
}

function spacer() {
  return new Paragraph({ children: [new TextRun({ text: "", size: BODY_PT })] });
}

const children = [];

// ---------------------------------------------------------------- title
children.push(title("Project Report"));
children.push(title("Reproducing S3-FIFO: Cache Eviction Using Only FIFO Queues", true));

// ------------------------------------------- group member and contribution
children.push(heading("Group Member and Contribution"));
children.push(body(
  "[Your full name], [your eRaider]@ttu.edu, R#[________]. This was a one-person project, " +
  "so all work below was carried out by the single group member."
));
children.push(bullet(
  "Selected the paper and confirmed before starting that its evaluation could be reproduced on a laptop, " +
  "by checking the authors' simulator against the machine and measuring the size of each public dataset."
));
children.push(bullet(
  "Built the simulation harness: the trace registry and loader, the one-hit-wonder analysis, " +
  "the miss ratio experiment across 12 algorithms, and the small-queue parameter sweep."
));
children.push(bullet(
  "Implemented S3-FIFO independently from Algorithm 1 of the paper and validated it against the " +
  "authors' reference C++ implementation, which is how the two ambiguities in the paper were found."
));
children.push(bullet(
  "Ran all simulations: 120 traces, 2.52 billion requests, 12 algorithms at two cache sizes."
));
children.push(bullet(
  "Produced every figure in this report, compared each against the original, and wrote the analysis " +
  "of where the results differ and why."
));
children.push(bullet("Wrote this report and the presentation slides."));

// ------------------------------------------------------- problem statement
children.push(heading("Problem Statement"));
children.push(body(
  "A cache is a small, fast store placed in front of a slower one. Web services put caches in front of " +
  "databases, content delivery networks put them in front of origin servers, and operating systems put " +
  "them in front of disks. Because a cache is always far smaller than the data people ask for, it runs " +
  "full almost immediately, and from then on every object admitted means another object must be thrown " +
  "out. The rule that picks the victim is the eviction algorithm. It is the single biggest lever on the " +
  "miss ratio, which is the fraction of requests the cache fails to serve. A lower miss ratio means fewer " +
  "slow trips to the backend, less load on that backend, and lower latency for the user, so a small " +
  "improvement in the eviction algorithm is worth a lot at scale."
));
children.push(body(
  "For most of the last thirty years that rule has been a variant of Least Recently Used. LRU keeps " +
  "objects in a queue ordered by how recently they were accessed and evicts from the tail, on the " +
  "assumption that recently used data will be used again. A long line of research has tried to beat it: " +
  "ARC, 2Q, SLRU, LIRS, TinyLFU, LeCaR, CACHEUS and LHD among others. Nearly all of them are built out " +
  "of one or more LRU queues with extra bookkeeping layered on top."
));
children.push(body(
  "The paper argues that this whole family has been optimising the wrong thing. Chasing miss ratio alone " +
  "has made these algorithms expensive in three ways that matter in production. The first is memory. An " +
  "LRU queue is normally a doubly linked list, so every cached object carries two pointers. When the " +
  "cached objects are themselves small, which is the common case in key-value caches, that overhead eats " +
  "a real fraction of the cache. The second is throughput. LRU has to move an object to the head of the " +
  "queue on every cache hit, which is a write to shared state and therefore needs a lock, on the hot " +
  "path, on the operation that is supposed to be fast. This is why LRU does not scale well across cores. " +
  "The third is complexity. These algorithms have parameters that are difficult to tune and they are " +
  "difficult to implement correctly; the authors note that implementations of LIRS used in earlier " +
  "published work contained two separate bugs. An algorithm that is hard to get right is one that " +
  "production engineers avoid, which is why many real systems still run plain FIFO or LRU and simply " +
  "accept the worse miss ratio."
));
children.push(body(
  "The observation the paper builds on reframes what the eviction algorithm is actually for. A " +
  "one-hit wonder is an object that is requested once and never again. Measured over a complete trace, " +
  "roughly a quarter of objects are one-hit wonders, which does not sound like a crisis. But a cache " +
  "never sees a complete trace. It sees a sliding window roughly the size of its own capacity. Measured " +
  "over a window containing 10% of a trace's distinct objects, 72% of the objects in that window are " +
  "one-hit wonders, and over a 1% window it is 78%. In other words most of what a cache admits is " +
  "worthless, and the real job is not choosing which valuable object to keep but getting rid of the " +
  "worthless ones fast, before they occupy space a useful object could have used. The authors call this " +
  "quick demotion, and it is the idea the rest of the paper follows from."
));

// -------------------------------------------------------- problem solution
children.push(heading("Problem Solution"));
children.push(body(
  "S3-FIFO is built from three FIFO queues and nothing else. There is no LRU queue anywhere in it, and " +
  "no object is ever moved because it was read. The three queues are a small queue S holding 10% of the " +
  "cache, a main queue M holding the other 90%, and a ghost queue G which stores keys only, with no data, " +
  "and is sized to hold as many entries as M."
));
children.push(...figure(
  path.join(FIG, "design_s3fifo.png"),
  "Figure 1. The three queues of S3-FIFO. Our own diagram, drawn to explain the algorithm."
));
children.push(body(
  "A new object is inserted into S, the probationary queue, unless its key is already in G, in which " +
  "case it is inserted straight into M instead. Each cached object carries a counter of two bits, capped " +
  "at a value of 3. A cache hit does one thing only: it increments that counter. Nothing is moved and no " +
  "list is re-linked, which is what allows a hit to proceed without taking a lock, and is the source of " +
  "the algorithm's scalability."
));
children.push(body(
  "Evictions are where the design shows its intent. When S is full, the object at its tail is examined. " +
  "If it was requested while it sat in S, it has proved itself and is promoted into M. If it was never " +
  "requested, which is the common case given the one-hit-wonder numbers above, the object is discarded " +
  "and only its key is kept, pushed into the ghost queue G. The point of G is that it gives the cache a " +
  "cheap memory of what it has already seen. If that same key is requested again later, the cache knows " +
  "the object is not a one-hit wonder after all, and admits it directly into M, skipping probation. " +
  "Evicting from M works like a clock sweep: the tail object is reinserted at the head with its counter " +
  "decremented if the counter is above zero, and is evicted outright once the counter reaches zero."
));
children.push(body(
  "The result is that unproven objects get a short, bounded stay in a small part of the cache, and only " +
  "objects that have demonstrated reuse are allowed to occupy the bulk of it. That is quick demotion. " +
  "The cost is two bits per object instead of two pointers, and the entire algorithm is about forty lines " +
  "of pseudocode."
));
children.push(body(
  "We implemented S3-FIFO ourselves from the paper's Algorithm 1, in Python, and validated it against " +
  "the authors' reference C++ implementation on the same trace. Doing so uncovered two places where the " +
  "paper's prose and its pseudocode contradict each other. Section 4.1 says an object moves from S to M " +
  "if it was “accessed more than once”, which reads as a counter of at least one, while pseudocode line " +
  "23 requires the counter to be strictly greater than one. Separately, the prose states that the counter " +
  "is cleared when an object is promoted, and the pseudocode never mentions clearing it. We implemented " +
  "all four combinations and measured each against the reference."
));
children.push(table([3100, 2200, 2000, 2060], [
  ["Promotion rule", "Counter reset", "Worst gap", "Described in"],
  ["freq > 1", "Yes", "0.0014", "Neither alone"],
  ["freq > 0", "Yes", "0.0017", "Prose"],
  ["freq > 0", "No", "0.0055", "Neither"],
  ["freq > 1", "No", "0.0058", "Pseudocode"],
]));
children.push(spacer());
children.push(body(
  "The reading that matches the reference implementation, to within 0.0014 of absolute miss ratio, takes " +
  "the threshold from the pseudocode and the counter reset from the prose. Neither half of the paper " +
  "describes the algorithm correctly on its own, which is worth knowing for anyone implementing from it."
));

// -------------------------------------------------------- simulation result
children.push(heading("Simulation Result"));
children.push(body(
  "The paper evaluates 6594 traces drawn from 14 datasets, several terabytes in total, which is not " +
  "something a laptop can replay. We selected the two datasets small enough to run and reproduced both " +
  "of them completely, every trace, rather than sampling. MSR Cambridge 2007 is 14 traces and 410 million " +
  "requests; CloudPhysics 2015 is 106 traces and 2114 million requests. Together that is 120 traces and " +
  "2.52 billion requests. Every algorithm was run at the two cache sizes the paper presents, 10% and 0.1% " +
  "of each trace's object count, with object size ignored, exactly as in the paper's section 5. " +
  "Simulations used the authors' own libCacheSim, so the algorithm implementations are theirs and the " +
  "experimental harness is ours. The complete run took about twenty hours on an eight-core laptop."
));
children.push(body(
  "One consequence of that selection matters for everything below and is worth stating up front: MSR and " +
  "CloudPhysics are both block storage workloads, whereas the paper's trace set is dominated by web and " +
  "key-value workloads. Block traces are markedly less skewed, which is precisely the condition under " +
  "which quick demotion pays off least. We are therefore testing S3-FIFO on the workloads least " +
  "favourable to it."
));

children.push(body("Pair 1: one-hit-wonder ratio (paper Figure 3 and Table 1).", { tight: true }));
children.push(...figure(path.join(PAPER, "paper_fig3.png"),
  "Figure 2a. Original: the paper's Figure 3, one-hit-wonder ratio across all 6594 traces."));
children.push(...figure(path.join(FIG, "fig3_one_hit_wonder.png"),
  "Figure 2b. Ours: the same measurement on MSR and CloudPhysics. Stars mark the paper's published values."));
children.push(body(
  "This measurement runs no cache simulation at all. It counts, for a window of a given length, what " +
  "fraction of the objects in that window appear exactly once. We ran it first precisely because it is " +
  "cheap and directly comparable, so it validates our trace decoding before any simulation result depends " +
  "on it. Both figures show the same shape: the one-hit-wonder ratio is very high for short windows and " +
  "falls as the window lengthens. The blue stars on our panels are the paper's own tabulated values, and " +
  "they sit on our means in every case."
));
children.push(table([2700, 2500, 1700, 1500, 960], [
  ["Dataset", "Window", "Paper", "Ours", "Difference"],
  ["MSR", "full trace", "0.56", "0.54", "-0.02"],
  ["MSR", "10% of objects", "0.74", "0.77", "+0.03"],
  ["MSR", "1% of objects", "0.86", "0.85", "-0.01"],
  ["CloudPhysics", "full trace", "0.40", "0.41", "+0.01"],
  ["CloudPhysics", "10% of objects", "0.71", "0.75", "+0.04"],
  ["CloudPhysics", "1% of objects", "0.80", "0.83", "+0.03"],
]));
children.push(spacer());
children.push(body(
  "All six values agree to within 0.04. Our MSR traces also total 409.8 million requests against the " +
  "410 million the paper reports for that dataset, which is strong evidence we are working from the same " +
  "underlying data. The small residual differences are expected: the paper samples windows at random and " +
  "averages over 100 repetitions, so the statistic is itself a sampled estimate, and our random draws are " +
  "not theirs."
));

children.push(body("Pair 2: miss ratio reduction from FIFO (paper Figure 6).", { tight: true }));
children.push(...figure(path.join(PAPER, "paper_fig6.png"),
  "Figure 3a. Original: the paper's Figure 6, percentiles of miss ratio reduction from FIFO."));
children.push(...figure(path.join(FIG, "fig6_miss_ratio_reduction.png"),
  "Figure 3b. Ours: the same percentiles over 120 traces."));
children.push(body(
  "This is the paper's central result. Because absolute miss ratios vary enormously between traces, both " +
  "the paper and we report the reduction relative to FIFO, using the paper's asymmetric definition that " +
  "bounds the value between -1 and 1 so that outliers cannot dominate the mean. On the large cache size, " +
  "the left panel in each figure, our ranking reproduces the paper's headline claim: S3-FIFO is first of " +
  "the eleven algorithms tested, with a mean reduction of 0.1479. The paper states a mean of 14% on the " +
  "large cache size, so our 14.8% is a direct match."
));
children.push(table([3000, 2400, 2000, 1960], [
  ["Rank", "Large cache (10%)", "Rank", "Small cache (0.1%)"],
  ["1. S3-FIFO", "0.1479", "1. 2Q", "0.0548"],
  ["2. TinyLFU", "0.1348", "2. S3-FIFO", "0.0533"],
  ["3. LIRS", "0.1307", "3. ARC", "0.0513"],
  ["4. ARC", "0.1128", "4. LHD", "0.0375"],
  ["5. 2Q", "0.1109", "5. SLRU", "0.0245"],
]));
children.push(spacer());
children.push(body(
  "A second feature visible in both figures supports the paper's robustness argument. S3-FIFO keeps a " +
  "positive P10 at both cache sizes, while TinyLFU and LIRS fall below zero there, meaning that on the " +
  "worst tenth of traces those two algorithms are actually worse than plain FIFO. S3-FIFO is never much " +
  "worse than the baseline, which is a property that matters more in production than a slightly better " +
  "average."
));
children.push(body(
  "The one place our result departs from the paper is the small cache size, where we find 2Q slightly " +
  "ahead of S3-FIFO, 0.0548 against 0.0533, whereas the paper has S3-FIFO first. The margin is small, but " +
  "the direction is a real difference and the explanation is the dataset selection described above. At a " +
  "cache holding only 0.1% of a trace's objects, a newly admitted object is evicted again very quickly, " +
  "so it often has no opportunity to demonstrate reuse before S discards it. 2Q does not suffer in the " +
  "same way because it reserves a fixed fraction of the cache for new objects. This effect is strongest " +
  "on workloads with little skew, which is exactly what block storage traces are. The paper's own " +
  "discussion of small cache sizes describes the same mechanism."
));

children.push(body("Pair 3: mean reduction per dataset (paper Figure 7).", { tight: true }));
children.push(...figure(path.join(PAPER, "paper_fig7.png"),
  "Figure 4a. Original: the paper's Figure 7, mean reduction per dataset, one row per dataset."));
children.push(...figure(path.join(FIG, "fig7_per_dataset.png"),
  "Figure 4b. Ours: mean reduction split by dataset at both cache sizes."));
children.push(body(
  "This pair is particularly useful because the paper publishes MSR and CloudPhysics as separate rows in " +
  "its own figure, so our two datasets can be checked against the paper individually rather than against " +
  "a pooled average over workloads we did not run. Our figure shows that the overall win is carried by " +
  "CloudPhysics. On MSR alone at the large cache size, ARC very slightly beats S3-FIFO, 0.132 against " +
  "0.131, a gap too small to be meaningful. On CloudPhysics S3-FIFO is clearly ahead, 0.151 against 0.110. " +
  "Reading the corresponding rows of the paper's figure shows the same pattern, with S3-FIFO's lead over " +
  "the strongest LRU-based competitors narrowest on the block datasets. The agreement here is therefore " +
  "better than the pooled comparison in the previous pair suggests, and it confirms that the difference " +
  "we saw at the small cache size comes from which datasets we were able to run rather than from an error " +
  "in the reproduction."
));

children.push(body("Pair 4: size of the small FIFO queue (paper Figure 11).", { tight: true }));
children.push(...figure(path.join(PAPER, "paper_fig11.png"),
  "Figure 5a. Original: the paper's Figure 11, reduction against the size of the probationary queue."));
children.push(...figure(path.join(FIG, "fig11_small_queue.png"),
  "Figure 5b. Ours: mean reduction against the size of S, on the MSR dataset."));
children.push(body(
  "S3-FIFO has essentially one tunable parameter, the fraction of the cache given to S, which the paper " +
  "fixes at 10%. We swept it from 1% to 50% to test how much that choice matters."
));
children.push(table([2500, 2500, 2300, 2060], [
  ["Size of S", "Large cache", "Small cache", "Note"],
  ["0.01", "0.1336", "-0.0008", ""],
  ["0.05", "0.1373", "0.0189", "best, large"],
  ["0.10", "0.1312", "0.0239", "paper's choice"],
  ["0.25", "0.1186", "0.0259", "best, small"],
  ["0.50", "0.0858", "0.0237", ""],
]));
children.push(spacer());
children.push(body(
  "Taken at face value this looks like a disagreement, since our best setting is 5% on the large cache " +
  "and 25% on the small one rather than the 10% the paper uses. It is worth being careful about what the " +
  "paper actually claims. Section 6.2 states that S3-FIFO is not sensitive to the size of S, and the " +
  "paper's own figure shows a mean line that is close to flat across a wide range of settings before " +
  "falling away. It does not claim that 10% is optimal on every workload. Our curve is flat in the same " +
  "way, and 10% is within about 0.6 percentage points of the best setting at both cache sizes. The result " +
  "therefore confirms the claim that was made, which is insensitivity, rather than contradicting it. What " +
  "our data adds is that the location of the shallow optimum moves with cache size, so 10% reads as a " +
  "sensible compromise rather than a tuned value."
));

children.push(body(
  "Two further differences are worth recording. First, the public MSR dataset contains 14 traces that all " +
  "clear the paper's stated cutoff of one million requests, whereas Table 1 of the paper reports 13; since " +
  "our request total matches theirs almost exactly, this appears to be a bookkeeping difference rather " +
  "than a different corpus. Second, while decoding the traces we found that the public dataset is not " +
  "internally consistent about its next-access index: the MSR files number requests from zero and the " +
  "CloudPhysics files number them from one. Assuming a single convention silently corrupts every " +
  "next-access pointer in one of the two datasets, so our loader detects the convention per trace and " +
  "cross-checks the result against an independent object count."
));

// -------------------------------------------------------------- conclusion
children.push(heading("Conclusion"));
children.push(body(
  "The paper's central claim reproduces. On the large cache size, across 120 traces and 2.52 billion " +
  "requests, S3-FIFO achieves the lowest miss ratio of the eleven algorithms we tested, beating ARC, " +
  "LIRS, TinyLFU, LHD and CACHEUS, and our mean reduction over FIFO of 14.8% matches the 14% the paper " +
  "reports. It does this while being markedly simpler than any of them: three FIFO queues, two bits of " +
  "metadata per object, no locking on cache hits, and about forty lines of pseudocode. The one-hit-wonder " +
  "measurement that motivates the design reproduces to within 0.04 on all six published values."
));
children.push(body(
  "The result is qualified in one place. At a very small cache size on block storage workloads, 2Q " +
  "overtakes S3-FIFO by a narrow margin. We do not read this as a failure of the paper. Both datasets we " +
  "were able to run are block workloads, which are far less skewed than the web and key-value traces that " +
  "dominate the paper's evidence, and skew is what quick demotion exploits. The paper's own per-dataset " +
  "figure shows the same narrowing on the same datasets. If anything, that S3-FIFO still wins at the " +
  "large cache size on the workloads least suited to it strengthens rather than weakens the paper's case."
));
children.push(body(
  "Reproducing the work also surfaced three things that are not visible from reading it. The paper's " +
  "prose and pseudocode disagree in two places, and the correct implementation takes one detail from each. " +
  "The public trace dataset uses two different indexing conventions without documenting the difference. " +
  "And the evaluation, which at first looks like it needs a cluster, can be reproduced in full on two of " +
  "its fourteen datasets using a laptop and about twenty hours, because the authors released both their " +
  "simulator and their traces. That last point is the most encouraging one: a paper is far easier to " +
  "trust when you can run it yourself."
));

// -------------------------------------------------------------- references
children.push(heading("References"));
children.push(body(
  "[1] Our reproduction code and results: [add your repository URL]. " +
  "The authors' original artifact is at https://github.com/Thesys-lab/sosp23-s3fifo.",
  { tight: true }
));
children.push(body(
  "[2] J. Yang, Y. Zhang, Z. Qiu, Y. Yue, and K. V. Rashmi, “FIFO queues are all you need for cache " +
  "eviction,” in Proc. 29th ACM Symposium on Operating Systems Principles (SOSP ’23), Koblenz, Germany, " +
  "Oct. 2023, pp. 130-149. doi: 10.1145/3600006.3613147.",
  { tight: true }
));
children.push(body(
  "[3] J. Yang, Y. Yue, and K. V. Rashmi, “libCacheSim: a high-performance library for building cache " +
  "simulators,” 2023. [Online]. Available: https://github.com/1a1a11a/libCacheSim",
  { tight: true }
));
children.push(body(
  "[4] Cache trace datasets (MSR Cambridge 2007 and CloudPhysics 2015), distributed by the libCacheSim " +
  "authors. [Online]. Available: https://github.com/cacheMon/cache_dataset",
  { tight: true }
));

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: BODY_PT } } } },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 } } },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("  wrote " + OUT + " (" + (buf.length / 1024).toFixed(0) + " KB)");
});
