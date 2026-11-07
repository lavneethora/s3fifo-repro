"""Turn the HTML deck into a .pptx for submission.

The HTML is the source of truth. Headless Chrome prints it to a 16:9 PDF (the
@page rule in build_slides.py sets 1920x1080), each page is rasterised, and each
image becomes one full-bleed PowerPoint slide. Speaker notes are carried across
from the slide definitions, so the notes pane works in PowerPoint too.

Slides are pictures, so the text is not editable in PowerPoint. That is the
trade for keeping the design exactly as authored.

  python slides/build_pptx.py          # needs the preview server running

Prerequisites: Google Chrome, pdftoppm (poppler), python-pptx.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile

from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_slides import SLIDES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "slides", "index.html")
OUT = os.path.join(ROOT, "slides", "S3-FIFO_Reproduction_Slides.pptx")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 16:9 widescreen, the PowerPoint default
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
DPI = 96          # 1440pt at 96dpi lands exactly on 1920px


def render_pdf(tmp):
    """Print the deck to a 16:9 PDF with headless Chrome."""
    pdf = os.path.join(tmp, "deck.pdf")
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf}", "--virtual-time-budget=20000",
         "file://" + HTML],
        check=True, capture_output=True,
    )
    return pdf


def rasterise(pdf, tmp):
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI), pdf,
                    os.path.join(tmp, "page")], check=True)
    return sorted(glob.glob(os.path.join(tmp, "page-*.png")))


def build():
    if not os.path.exists(CHROME):
        sys.exit("Google Chrome not found at " + CHROME)
    if shutil.which("pdftoppm") is None:
        sys.exit("pdftoppm not found; install poppler")

    with tempfile.TemporaryDirectory() as tmp:
        pages = rasterise(render_pdf(tmp), tmp)
        if len(pages) != len(SLIDES):
            print(f"  warning: {len(pages)} pages rendered for {len(SLIDES)} slides")

        prs = Presentation()
        prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
        blank = prs.slide_layouts[6]

        for i, page in enumerate(pages):
            slide = prs.slides.add_slide(blank)
            slide.shapes.add_picture(page, 0, 0, width=SLIDE_W, height=SLIDE_H)
            if i < len(SLIDES):
                slide.notes_slide.notes_text_frame.text = SLIDES[i]["notes"]

        prs.save(OUT)

    kb = os.path.getsize(OUT) / 1024
    print(f"  wrote {OUT} ({kb:.0f} KB, {len(pages)} slides, notes included)")


if __name__ == "__main__":
    build()
