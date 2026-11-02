"""Draw the S3-FIFO design diagram used in the report.

Not a reproduction of a paper figure. This is our own drawing of the three
queues, for explaining the algorithm in our own words.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGURES = os.path.join(ROOT, "figures")

INK = "#16202B"
BODY = "#4A5765"
ORANGE = "#C25B1E"
BLUE = "#2E6DA4"
GREY = "#7E8B99"


def box(ax, x, y, w, h, label, sub, edge, fill="#FFFFFF", dashed=False):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=2.2, edgecolor=edge, facecolor=fill,
        linestyle="--" if dashed else "-"))
    ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center",
            fontsize=15, fontweight="bold", color=edge)
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
            fontsize=10.5, color=BODY)


def arrow(ax, start, end, color=INK, style="-", rad=0.0, label=None,
          label_pos=None, label_color=None):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=16, linewidth=1.8,
        color=color, linestyle=style,
        connectionstyle=f"arc3,rad={rad}"))
    if label:
        lx, ly = label_pos
        ax.text(lx, ly, label, ha="center", va="center", fontsize=10.5,
                color=label_color or color)


def main():
    fig, ax = plt.subplots(figsize=(12.4, 4.4))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 4.4)
    ax.axis("off")

    box(ax, 1.5, 2.5, 2.2, 1.2, "S", "small FIFO, 10%", ORANGE)
    box(ax, 5.4, 2.5, 3.4, 1.2, "M", "main FIFO, 90%", BLUE)
    box(ax, 5.4, 0.5, 3.4, 1.0, "G", "ghost queue, keys only", GREY, "#F0F2EF", True)

    arrow(ax, (0.35, 3.1), (1.45, 3.1))
    ax.text(0.35, 3.45, "new object", ha="left", va="center", fontsize=11, color=BODY)

    arrow(ax, (3.75, 3.15), (5.35, 3.15), color=BLUE,
          label="requested\nwhile in S", label_pos=(4.55, 3.62), label_color=BLUE)

    arrow(ax, (3.6, 2.45), (5.45, 1.35), color=ORANGE, rad=-0.18,
          label="never requested", label_pos=(4.3, 1.75), label_color=ORANGE)

    arrow(ax, (8.85, 1.2), (8.95, 2.55), color=GREY, rad=0.35)
    ax.text(10.35, 1.95, "key seen before:\nskip probation",
            ha="left", va="center", fontsize=10.5, color=GREY)

    arrow(ax, (8.85, 3.4), (10.25, 3.4))
    ax.text(10.35, 3.4, "evicted", ha="left", va="center", fontsize=11, color=BODY)

    ax.text(6.2, 0.08,
            "A cache hit only increments a 2-bit counter, capped at 3. Nothing moves, so hits need no lock.",
            ha="center", va="bottom", fontsize=10.5, color=BODY, style="italic")

    os.makedirs(FIGURES, exist_ok=True)
    path = os.path.join(FIGURES, "design_s3fifo.png")
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    print(f"  wrote {path}")
    return path


if __name__ == "__main__":
    main()
