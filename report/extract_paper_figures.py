"""Crop the original figures out of the paper PDF for side-by-side comparison.

The report has to show each of the paper's figures next to ours, so the
originals are rendered from the PDF rather than stored in this repository.
Download the paper first:

  https://www.cs.cmu.edu/~rvinayak/papers/s3-fifo-sosp-2023-fifo-queues-are-all-you-need-for-cache-eviction.pdf

then run:  python report/extract_paper_figures.py <path-to-pdf>

Boxes are in points of a 150 dpi render and are scaled to whatever dpi is used.
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image

DPI = 300
SCALE = DPI / 150

# figure name -> (page, crop box in 150 dpi pixels)
FIGURES = {
    "paper_fig3": (4, (650, 492, 1172, 680)),
    "paper_fig6": (8, (105, 133, 1172, 385)),
    "paper_fig7": (10, (105, 133, 1172, 385)),
    "paper_fig11": (13, (105, 133, 1172, 372)),
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_figures")


def main(pdf_path):
    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, (page, box) in FIGURES.items():
            prefix = os.path.join(tmp, name)
            subprocess.run(
                ["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI),
                 "-png", pdf_path, prefix],
                check=True,
            )
            rendered = [f for f in os.listdir(tmp)
                        if f.startswith(os.path.basename(prefix))]
            src = os.path.join(tmp, rendered[0])
            scaled = tuple(int(v * SCALE) for v in box)
            out = os.path.join(OUT_DIR, name + ".png")
            Image.open(src).crop(scaled).convert("RGB").save(out)
            print(f"  wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python report/extract_paper_figures.py <paper.pdf>")
    main(sys.argv[1])
