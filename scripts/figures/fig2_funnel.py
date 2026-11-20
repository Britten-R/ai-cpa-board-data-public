"""Figure 2, "From Talk to Rules": six levels, from all 55 boards down to boards with an AI-specific rule.

Every number is computed from data/tier1_coding.csv (one row per Tier 1 document: date, binding status,
who is speaking, topic) and data/jurisdictions.csv. No number is typed in. National (NASBA, AICPA) rows are
left out; only state and territorial boards are counted.

Levels, top to bottom:
  1. All boards                                  unique jurisdictions in data/jurisdictions.csv
  2. Document mentioning AI since 2023           a Tier 1 document dated 2023 or later
  3. ...where the board itself is speaking       speaker = board_authored, board_discussion or individual_statement
  4. ...about CPAs using AI                      as 3, and topic = cpa_use_of_ai
  5. Published its own guidance                  binding status = guidance and speaker = board_authored
     note on the bar: drafts                     draft_own_guidance = yes (a board-written draft not yet issued)
  6. AI-specific rule                            binding status = rule

Run from the repo root:  python scripts/figures/fig2_funnel.py
Writes docs/figures/fig2_funnel.{png,svg,csv}. Checks that level 2 equals categories 1 + 2 of
docs/figures/fig1_map.csv (run fig1_map.py first) and stops if not.
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

NAT = ("National (NASBA)", "National (AICPA)")
OWN = {"board_authored", "board_discussion", "individual_statement"}
OUT_DIR = "docs/figures"
TITLE = "From Talk to Rules: How 55 Accountancy Boards Have Responded to AI"


def strip_svg_metadata(path):
    """Remove the <metadata> block that matplotlib writes (software name and date), so the SVG is reproducible."""
    import re
    with open(path, encoding="utf-8") as f:
        svg = f.read()
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(re.sub(r"\s*<metadata>.*?</metadata>", "", svg, flags=re.S))


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute():
    juris = rd("data/jurisdictions.csv")
    co = rd("data/tier1_coding.csv")
    board = [c for c in co if c["jurisdiction"] not in NAT]
    since = [c for c in board if c["date"][:4].isdigit() and c["date"][:4] >= "2023"]
    J = lambda rows: sorted({c["jurisdiction"] for c in rows})  # noqa: E731

    s1 = sorted({r["jurisdiction"] for r in juris})
    s2 = J(since)
    s4 = J([c for c in since if c["speaker"] in OWN])
    s5 = J([c for c in since if c["speaker"] in OWN and c["topic"] == "cpa_use_of_ai"])
    s6 = J([c for c in board if c["binding_status"] == "guidance" and c["speaker"] == "board_authored"])
    drafts = J([c for c in board if c["draft_own_guidance"] == "yes" and c["jurisdiction"] not in s6])
    rule_t1 = {c["jurisdiction"] for c in board if c["binding_status"] == "rule"}
    s7 = sorted(rule_t1)

    return [
        (1, "All state and territorial boards", "all boards", s1),
        (2, "Boards with a document mentioning AI since 2023", "Tier 1 document dated 2023+", s2),
        (3, "…where the board itself is speaking", "board itself speaking", s4),
        (4, "…where the board is speaking about CPAs using AI", "board speaking, CPAs using AI", s5),
        (5, "Boards that published their own guidance", "board-authored guidance (note: drafts)", s6, drafts),
        (6, "Boards with an AI-specific rule", "AI-specific rule", s7),
    ]


def check_against_map(levels):
    """Level 2 must equal the coral + peach count (categories 1 and 2) on the Figure 1 map."""
    mp = rd("docs/figures/fig1_map.csv")
    on_map = sorted(r["jurisdiction"] for r in mp if r["category"] in ("1", "2"))
    s2 = levels[1][3]
    if s2 != on_map:
        sys.exit(f"STOP: level 2 = {len(s2)} but the map shows {len(on_map)}. "
                 f"Only in funnel: {sorted(set(s2) - set(on_map))}; only on map: {sorted(set(on_map) - set(s2))}")
    print(f"check: level 2 = {len(s2)} = map categories 1 + 2")


def write_csv(levels, path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "label", "boards", "definition", "jurisdictions", "note"])
        for lvl, label, defn, s, *rest in levels:
            note = f"plus {len(rest[0])} draft ({'; '.join(rest[0])})" if rest and rest[0] else ""
            w.writerow([lvl, label, len(s), defn, "; ".join(s) if lvl > 1 else "all 55", note])


def draw(levels, base):
    plt.rcParams.update({"font.family": "serif",
                         "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
                         "svg.fonttype": "none"})
    ink, muted = "#1A1A1A", "#555555"
    fill = {1: "#D9D4CE", 2: "#F6CBA8", 3: "#F6CBA8", 4: "#F6CBA8", 5: "#E8998D", 6: "#E8998D"}
    total = len(levels[0][3])

    fig = plt.figure(figsize=(10, 5.6), dpi=160)  # 10 in x 160 dpi = 1600 px wide
    fig.patch.set_facecolor("white")
    # label column on the left, bar area on the right
    ax = fig.add_axes([0.43, 0.15, 0.50, 0.68])
    ax.set_facecolor("white")
    ax.set_xlim(0, total * 1.12)
    ax.set_ylim(len(levels) - 0.4, -0.6)

    for i, (lvl, label, _, s, *rest) in enumerate(levels):
        n = len(s)
        if n > 0:
            ax.barh(i, n, height=0.62, color=fill[lvl], edgecolor="none")
        ax.text(n + total * 0.015, i, str(n), va="center", ha="left",
                fontsize=15, color=ink, fontweight="normal" if lvl <= 4 else "bold")
        if rest and rest[0]:
            names = ", ".join(rest[0])
            ax.text(n + total * 0.065, i, f"plus {len(rest[0])} draft ({names})", va="center", ha="left",
                    fontsize=11, style="italic", color=muted)
        ax.text(-total * 0.03, i, label, va="center", ha="right", fontsize=12.5,
                color=ink, fontweight="normal" if lvl <= 4 else "bold")

    ax.axis("off")
    fig.text(0.03, 0.93, TITLE, fontsize=17, fontweight="bold", color=ink, ha="left", va="center")
    fig.text(0.03, 0.05,
             "Source: public records of 55 state and territorial accountancy boards, "
             "January 2023 to November 2026.",
             fontsize=10, color=muted, ha="left", va="center")
    fig.savefig(base + ".png", dpi=160, facecolor="white")
    fig.savefig(base + ".svg", facecolor="white")
    strip_svg_metadata(base + ".svg")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, "fig2_funnel")
    levels = compute()
    check_against_map(levels)
    write_csv(levels, base + ".csv")
    draw(levels, base)
    for lvl, label, defn, s, *rest in levels:
        print(f"{lvl}\t{len(s)}\t{defn}\t{label}\t{', '.join(s) if lvl > 1 else ''}")


if __name__ == "__main__":
    main()
