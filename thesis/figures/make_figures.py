import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from pathlib import Path

out = Path(__file__).resolve().parent

# Common style without specifying colors to satisfy general plotting guidance.
plt.rcParams.update({
    "font.size": 10,
    "figure.dpi": 160,
    "savefig.bbox": "tight",
})

def add_box(ax, xy, w, h, text, fontsize=9):
    box = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02", linewidth=1.2, facecolor="white", edgecolor="black")
    ax.add_patch(box)
    ax.text(xy[0]+w/2, xy[1]+h/2, text, ha="center", va="center", fontsize=fontsize)
    return box

def add_arrow(ax, start, end):
    arr = FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=14, linewidth=1.1, color="black")
    ax.add_patch(arr)

# Figure 1: overall framework
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
add_box(ax, (0.4, 3.3), 2.1, 0.85, "Patent documents\nTitle / Abstract / Claims")
add_box(ax, (3.0, 3.3), 2.1, 0.85, "LLM extraction\nproblem / solution")
add_box(ax, (5.6, 3.3), 2.1, 0.85, "Embedding\nBERT / PatentSBERTa")
add_box(ax, (8.2, 3.3), 1.4, 0.85, "Candidate\nranking")
add_arrow(ax, (2.5, 3.72), (3.0, 3.72)); add_arrow(ax, (5.1, 3.72), (5.6, 3.72)); add_arrow(ax, (7.7, 3.72), (8.2, 3.72))
add_box(ax, (2.1, 1.4), 2.6, 0.85, "Problem vector\nWhat problem is solved?")
add_box(ax, (5.3, 1.4), 2.6, 0.85, "Solution vector\nHow is it solved?")
add_arrow(ax, (4.05, 3.3), (3.4, 2.25)); add_arrow(ax, (4.05, 3.3), (6.6, 2.25))
add_box(ax, (0.6, 0.2), 2.6, 0.75, "Close-solution type\nExample: U-Net")
add_box(ax, (6.8, 0.2), 2.6, 0.75, "Different-solution type\nExample: Kao cleaning")
add_arrow(ax, (3.4, 1.4), (1.9, 0.95)); add_arrow(ax, (6.6, 1.4), (8.1, 0.95))
ax.text(5, 4.65, "Problem--Solution Decomposed Candidate Extraction", ha="center", va="center", fontsize=13, weight="bold")
fig.savefig(out/"fig01_framework.png")
plt.close(fig)

# Figure 2: problem solution split
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.set_xlim(0, 9); ax.set_ylim(0, 5); ax.axis("off")
add_box(ax, (0.4, 3.5), 2.2, 0.8, "Original patent text")
add_box(ax, (3.4, 3.9), 2.4, 0.7, "Problem context")
add_box(ax, (3.4, 2.9), 2.4, 0.7, "Solution context")
add_box(ax, (3.4, 1.9), 2.4, 0.7, "Technical means")
add_box(ax, (6.6, 3.9), 1.9, 0.7, "Problem vector")
add_box(ax, (6.6, 2.9), 1.9, 0.7, "Solution vector")
add_box(ax, (6.6, 1.9), 1.9, 0.7, "Candidate label")
for y in [4.25,3.25,2.25]:
    add_arrow(ax, (2.6, 3.9), (3.4, y))
add_arrow(ax, (5.8, 4.25), (6.6, 4.25)); add_arrow(ax, (5.8, 3.25), (6.6, 3.25)); add_arrow(ax, (5.8, 2.25), (6.6, 2.25))
ax.text(0.55, 2.2, "Background / Object\nSummary / Claims", ha="left", fontsize=9)
ax.text(4.6, 0.65, "Claims are mainly used for solution/configuration.\nProblem is often in Abstract, Background, and Object sections.", ha="center", fontsize=9)
fig.savefig(out/"fig02_problem_solution_split.png")
plt.close(fig)

# Figure 3: evaluation design timeline
fig, ax = plt.subplots(figsize=(9, 3.3))
ax.set_xlim(2014.5, 2024.5); ax.set_ylim(0, 3); ax.set_yticks([])
ax.set_xticks(range(2015, 2025)); ax.grid(axis='x', linestyle=':', linewidth=0.5)
ax.hlines(2, 2015, 2018, linewidth=8, alpha=0.5)
ax.hlines(1, 2019, 2024, linewidth=8, alpha=0.5)
ax.text(2016.5, 2.25, "Past window\n2015--2018\nCandidate extraction", ha="center", va="bottom", fontsize=11)
ax.text(2021.5, 1.25, "Future window\n2019--2024\nRetrospective evaluation", ha="center", va="bottom", fontsize=11)
ax.annotate("U-Net absent in target field\n(manufacturing defects)", xy=(2018,2), xytext=(2018.8,2.55), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.annotate("U-Net appears after 2019", xy=(2019,1), xytext=(2016.1,0.35), arrowprops=dict(arrowstyle="->"), fontsize=9)
ax.set_title("Retrospective Evaluation Design")
ax.set_xlabel("Filing year")
fig.savefig(out/"fig03_evaluation_design.png")
plt.close(fig)

# U-Net annual rates publication
years = np.array([2015,2016,2017,2018,2019,2020,2021,2022,2023,2024])
A0 = np.array([472,446,667,930,1514,1696,1986,2182,2437,2837])
A1 = np.array([0,0,1,24,59,74,110,153,171,212])
B0 = np.array([351,468,571,681,975,1165,1380,1791,2236,2594])
B1 = np.array([0,0,0,0,3,10,13,11,16,19])
med_rate = A1 / A0 * 100
man_rate = B1 / B0 * 100
fig, ax = plt.subplots(figsize=(8,4.6))
ax.plot(years, med_rate, marker='o', label="Medical image analysis")
ax.plot(years, man_rate, marker='o', label="Manufacturing defect detection")
ax.set_title("Annual U-Net Patent Share (Publication basis)")
ax.set_xlabel("Filing year"); ax.set_ylabel("U-Net share (%)")
ax.set_xticks(years); ax.grid(True, linewidth=0.5, alpha=0.5); ax.legend()
fig.savefig(out/"fig04_unet_publication_rate.png")
plt.close(fig)

# Publication period comparison
labels = ["2015--2018", "2019--2024"]
med_period = [25/2515*100, 779/12652*100]
man_period = [0/2071*100, 72/10141*100]
x = np.arange(len(labels)); width=0.35
fig, ax = plt.subplots(figsize=(7.4,4.4))
ax.bar(x-width/2, med_period, width, label="Medical")
ax.bar(x+width/2, man_period, width, label="Manufacturing")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("U-Net share (%)")
ax.set_title("Period Comparison of U-Net Share (Publication basis)")
ax.legend(); ax.grid(axis='y', linewidth=0.5, alpha=0.5)
for xi, v in zip(x-width/2, med_period): ax.text(xi, v+0.08, f"{v:.2f}%", ha='center', va='bottom', fontsize=9)
for xi, v in zip(x+width/2, man_period): ax.text(xi, v+0.08, f"{v:.2f}%", ha='center', va='bottom', fontsize=9)
fig.savefig(out/"fig05_unet_period_publication.png")
plt.close(fig)

# Family period comparison
med_family = [14/1128*100, 563/7385*100]
man_family = [0/1420*100, 49/7478*100]
fig, ax = plt.subplots(figsize=(7.4,4.4))
ax.bar(x-width/2, med_family, width, label="Medical")
ax.bar(x+width/2, man_family, width, label="Manufacturing")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("U-Net share (%)")
ax.set_title("Period Comparison of U-Net Share (Family ID basis)")
ax.legend(); ax.grid(axis='y', linewidth=0.5, alpha=0.5)
for xi, v in zip(x-width/2, med_family): ax.text(xi, v+0.08, f"{v:.2f}%", ha='center', va='bottom', fontsize=9)
for xi, v in zip(x+width/2, man_family): ax.text(xi, v+0.08, f"{v:.2f}%", ha='center', va='bottom', fontsize=9)
fig.savefig(out/"fig06_unet_period_family.png")
plt.close(fig)

# Dataset overview bar
names = ["A0", "A1", "B0", "B1"]
values = [15167, 804, 12212, 72]
fig, ax = plt.subplots(figsize=(7,4.2))
ax.bar(names, values)
ax.set_yscale('log')
ax.set_ylabel("Publication count (log scale)")
ax.set_title("Dataset Size Overview")
for i, v in enumerate(values): ax.text(i, v*1.08, f"{v:,}", ha='center', fontsize=9)
fig.savefig(out/"fig07_dataset_overview.png")
plt.close(fig)

print("Figures written to", out)
