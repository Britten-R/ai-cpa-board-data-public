"""Figure 1 (map): "What 55 Accountancy Boards Have Said About AI."

Every jurisdiction is put into exactly one category, computed from data/:
  1. Wrote or drafted its own guidance   named: Texas, Virginia
  2. AI appears in board records         any other board with a Tier 1 document dated 2023 or later
                                         (data/tier1_board_ai_guidance.csv, national rows excluded)
  3. No AI mention found                 boards with collected records and no Tier 1 document dated 2023+
  4. Records not obtained                named: Guam, Kentucky, Northern Mariana Islands, U.S. Virgin Islands,
                                         Puerto Rico. If one of these has a 2023+ Tier 1 document it goes
                                         to category 2 instead, and the script says so.
"Collected records" for category 3 is checked against data/tier2_meeting_index.csv and
data/tier2_intake_index.csv; a category 3 board with neither is printed as a warning.

State shapes: U.S. Census cartographic boundary file cb_2016_us_state_500k, shipped inside the
plotly-geo package (pip install plotly-geo pyshp); nothing is downloaded at run time.

Run from the repo root:  python scripts/figures/fig1_map.py
Writes docs/figures/fig1_map.{png,svg,csv}.
"""
import csv
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path  # noqa: E402

import _plotly_geo  # noqa: E402
import shapefile  # noqa: E402  (pyshp)

OUT_DIR = "docs/figures"
TITLE = "What 55 Accountancy Boards Have Said About AI"
CAPTION = ("North Carolina reprinted the AICPA's guidance, which is available to every state, "
           "so it is shown with boards whose records mention AI.")
SOURCE = ("Source: public records of 55 state and territorial accountancy boards, January 2023 to "
          "November 2026.")
NAT = ("National (NASBA)", "National (AICPA)")
OWN_GUIDANCE = ["Texas", "Virginia"]
NOT_OBTAINED = ["Guam", "Kentucky", "Northern Mariana Islands", "U.S. Virgin Islands", "Puerto Rico"]
CATS = [
    (1, "Wrote or drafted its own guidance", "#E8998D"),
    (2, "AI appears in board records", "#F6CBA8"),
    (3, "No AI mention found", "#F7EDD0"),
    (4, "Records not obtained", "#D9D4CE"),
]
HATCH_COLOR = "#A39B91"   # a darker shade of the category 4 grey, for the diagonal lines
INK = "#1A1A1A"
MUTED = "#555555"
# jurisdiction name in data/ -> postal code in the shapefile
SHAPE_NAME = {"District of Columbia": "DC", "Puerto Rico": "PR", "Guam": "GU",
              "Northern Mariana Islands": "MP", "U.S. Virgin Islands": "VI"}
SQUARES = [("DC", "District of Columbia"), ("PR", "Puerto Rico"), ("GU", "Guam"),
           ("VI", "U.S. Virgin Islands"), ("MP", "Northern Mariana Islands")]


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


# ------------------------------------------------------------------ categories
def categorize():
    juris = sorted({r["jurisdiction"] for r in rd("data/jurisdictions.csv")})  # Illinois has two board rows
    assert len(juris) == 55, len(juris)
    t1 = rd("data/tier1_board_ai_guidance.csv")
    recent = {r["jurisdiction"] for r in t1 if r["jurisdiction"] not in NAT
              and r["date"][:4].isdigit() and r["date"][:4] >= "2023"}
    collected = ({r["jurisdiction"] for r in rd("data/tier2_meeting_index.csv")}
                 | {r["jurisdiction"] for r in rd("data/tier2_intake_index.csv")})
    for name in OWN_GUIDANCE + NOT_OBTAINED:
        assert name in juris, name
    cat, notes = {}, []
    for j in juris:
        if j in OWN_GUIDANCE:
            cat[j] = 1
        elif j in NOT_OBTAINED:
            if j in recent:
                cat[j] = 2
                notes.append(f"NOTE: {j} is on the records-not-obtained list but has a 2023+ Tier 1 document: category 2")
            else:
                cat[j] = 4
        elif j in recent:
            cat[j] = 2
        else:
            cat[j] = 3
            if j not in collected:
                notes.append(f"WARNING: {j} is in category 3 but has no collected meeting records in Tier 2 or the intake")
    for j in OWN_GUIDANCE:
        if j not in recent:
            notes.append(f"WARNING: {j} is named as category 1 but has no 2023+ Tier 1 document")
    return cat, notes


# ------------------------------------------------------------------ shapes
def albers(lon, lat, lon0, lat0, p1, p2):
    """Albers equal-area conic on a unit sphere (radius 6371 km), returns km."""
    R = 6371.0
    r = math.radians
    n = (math.sin(r(p1)) + math.sin(r(p2))) / 2
    C = math.cos(r(p1)) ** 2 + 2 * n * math.sin(r(p1))
    rho0 = R * math.sqrt(C - 2 * n * math.sin(r(lat0))) / n
    rho = R * math.sqrt(C - 2 * n * math.sin(r(lat))) / n
    th = n * r(lon - lon0)
    return rho * math.sin(th), rho0 - rho * math.cos(th)


def load_shapes():
    base = os.path.join(os.path.dirname(_plotly_geo.__file__), "package_data", "cb_2016_us_state_500k")
    sf = shapefile.Reader(base)
    out = {}
    for rec, shp in zip(sf.records(), sf.shapes()):
        parts = list(shp.parts) + [len(shp.points)]
        rings = [shp.points[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
        out[rec["STUSPS"]] = (rec["NAME"], rings)
    return out


def project_rings(code, rings):
    """Lower 48 in a standard Albers; Alaska and Hawaii in their own Albers, scaled and moved into insets
    below California/Arizona (Alaska) and west of Texas (Hawaii). Hawaii's uninhabited northwest islands
    (west of 161 W) are left out, as on most U.S. maps."""
    if code == "HI":
        rings = [r for r in rings if max(lon for lon, _ in r) > -161]
    proj = {"AK": lambda lo, la: albers(lo - 360 if lo > 0 else lo, la, -154, 50, 55, 65),
            "HI": lambda lo, la: albers(lo, la, -157, 13, 8, 18)}.get(
        code, lambda lo, la: albers(lo, la, -96, 37.5, 29.5, 45.5))
    res = [[proj(lon, lat) for lon, lat in ring] for ring in rings]
    if code in INSET:
        scale, (tx, ty) = INSET[code]
        x0 = min(x for r in res for x, _ in r)
        y0 = min(y for r in res for _, y in r)
        res = [[((x - x0) * scale + tx, (y - y0) * scale + ty) for x, y in r] for r in res]
    return [thin(r, 2.5) for r in res]


# inset scale and lower-left corner (km, in the lower-48 projection)
INSET = {"AK": (0.33, (-2350, -1390)), "HI": (1.0, (-1000, -1400))}


def thin(pts, tol):
    """Drop points closer than tol km to the last kept point (keeps files small; invisible at print size)."""
    if len(pts) < 8:
        return pts
    keep = [pts[0]]
    for p in pts[1:-1]:
        if math.hypot(p[0] - keep[-1][0], p[1] - keep[-1][1]) >= tol:
            keep.append(p)
    keep.append(pts[-1])
    return keep if len(keep) >= 4 else pts


def ring_area(pts):
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))


def label_point(rings):
    big = max(rings, key=lambda p: abs(ring_area(p)))
    a = ring_area(big)
    cx = sum((x1 + x2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(big, big[1:] + big[:1])) / (6 * a)
    cy = sum((y1 + y2) * (x1 * y2 - x2 * y1) for (x1, y1), (x2, y2) in zip(big, big[1:] + big[:1])) / (6 * a)
    return cx, cy


# label nudges (km) where the centroid sits badly, and small states labelled off the coast
NUDGE = {"FL": (90, -40), "LA": (-60, 0), "MI": (40, -60), "KY": (20, -10), "ID": (0, -60),
         "CA": (-20, 0), "WV": (-15, -10), "VA": (40, -10), "NY": (30, 0), "MN": (-20, 0),
         "HI": (0, 150), "AK": (0, 30), "OK": (40, 0), "TX": (20, -30), "MS": (0, 10), "SC": (10, 0),
         "TN": (10, 0), "NC": (40, 0), "PA": (0, 0), "ME": (10, 0)}
CALLOUT = {"VT": (1830, 1150), "NH": (2190, 940), "MA": (2290, 800), "RI": (2290, 690),
           "CT": (2290, 590), "NJ": (2190, 410), "DE": (2190, 300), "MD": (2190, 190)}


# ------------------------------------------------------------------ drawing
def draw(cat, base):
    plt.rcParams.update({"font.family": "serif",
                         "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
                         "svg.fonttype": "none", "hatch.linewidth": 0.6})
    color = {c: col for c, _, col in CATS}
    shapes = load_shapes()
    code_of = {name: code for code, (name, _) in shapes.items()}
    code_of.update({j: c for j, c in SHAPE_NAME.items()})

    W, H = 12.5, 8.0                      # 12.5 in x 160 dpi = 2000 px
    fig = plt.figure(figsize=(W, H), dpi=160)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.02, 0.255, 0.70, 0.645])
    ax.set_facecolor("white")
    ax.set_aspect("equal")
    ax.axis("off")

    def fill(c, verts_codes, hatch_ok=True):
        verts, codes = verts_codes
        path = Path(verts, codes)
        ax.add_patch(PathPatch(path, facecolor=color[c], edgecolor="white", linewidth=0.7, zorder=1))
        if c == 4 and hatch_ok:
            ax.add_patch(PathPatch(path, facecolor="none", edgecolor="none", hatch="////",
                                   hatchcolor=HATCH_COLOR, linewidth=0, zorder=2))
            ax.add_patch(PathPatch(path, facecolor="none", edgecolor="white", linewidth=0.7, zorder=3))

    allx, ally = [], []
    for j, c in cat.items():
        code = code_of[j]
        if code in SHAPE_NAME.values():
            continue                      # DC and the territories are drawn as squares
        rings = project_rings(code, shapes[code][1])
        verts, codes = [], []
        for ring in rings:
            verts += ring + [ring[0]]
            codes += [Path.MOVETO] + [Path.LINETO] * (len(ring) - 1) + [Path.CLOSEPOLY]
        fill(c, (verts, codes))
        allx += [v[0] for v in verts]
        ally += [v[1] for v in verts]
        if code in CALLOUT:
            lx, ly = CALLOUT[code]
            sx, sy = label_point(rings)
            ax.plot([sx, lx - 45], [sy, ly], color=MUTED, linewidth=0.5, zorder=4)
            ax.text(lx, ly, code, fontsize=9.5, ha="left", va="center", color=INK, zorder=5)
        else:
            x, y = label_point(rings)
            dx, dy = NUDGE.get(code, (0, 0))
            ax.text(x + dx, y + dy, code, fontsize=9.5, ha="center", va="center", color=INK, zorder=5)

    ax.set_xlim(min(allx) - 30, max(max(allx), max(x for x, _ in CALLOUT.values())) + 180)
    ax.set_ylim(min(ally) - 30, max(max(ally), max(y for _, y in CALLOUT.values())) + 30)
    ax.set_anchor("N")

    # row of squares for DC and the territories
    sq_ax = fig.add_axes([0.02, 0.135, 0.70, 0.085])
    sq_ax.set_xlim(0, 100)
    sq_ax.set_ylim(0, 10)
    sq_ax.axis("off")
    step = 100 / len(SQUARES)
    for i, (code, name) in enumerate(SQUARES):
        c = cat[name]
        x0 = i * step + step / 2 - 2.2
        kw = dict(facecolor=color[c], edgecolor="none")
        sq_ax.add_patch(Rectangle((x0, 4.2), 4.4, 5.2, **kw))
        if c == 4:
            sq_ax.add_patch(Rectangle((x0, 4.2), 4.4, 5.2, facecolor="none", edgecolor="none",
                                      hatch="////", hatchcolor=HATCH_COLOR, linewidth=0))
        sq_ax.text(x0 + 2.2, 6.8, code, fontsize=9.5, ha="center", va="center", color=INK)
        sq_ax.text(x0 + 2.2, 2.0, name, fontsize=10, ha="center", va="center", color=INK)

    # legend on the right, top to bottom in category order, with counts
    counts = {c: sum(1 for v in cat.values() if v == c) for c, _, _ in CATS}
    lg = fig.add_axes([0.745, 0.42, 0.24, 0.36])
    lg.set_xlim(0, 10)
    lg.set_ylim(0, 10)
    lg.axis("off")
    for k, (c, label, col) in enumerate(CATS):
        y = 8.9 - k * 2.5
        lg.add_patch(Rectangle((0, y - 0.55), 1.1, 1.1, facecolor=col, edgecolor="none"))
        if c == 4:
            lg.add_patch(Rectangle((0, y - 0.55), 1.1, 1.1, facecolor="none", edgecolor="none",
                                   hatch="////", hatchcolor=HATCH_COLOR, linewidth=0))
        lg.text(1.6, y + 0.15, label, fontsize=12, ha="left", va="bottom", color=INK)
        n = counts[c]
        lg.text(1.6, y - 0.1, f"{n} jurisdiction{'s' if n != 1 else ''}", fontsize=11,
                ha="left", va="top", color=MUTED)

    fig.text(0.03, 0.945, TITLE, fontsize=19, fontweight="bold", color=INK, ha="left", va="center")
    fig.text(0.03, 0.085, CAPTION, fontsize=11, style="italic", color=INK, ha="left", va="center")
    fig.text(0.03, 0.04, SOURCE, fontsize=10, color=MUTED, ha="left", va="center")
    fig.savefig(base + ".png", dpi=160, facecolor="white")
    fig.savefig(base + ".svg", facecolor="white")
    strip_svg_metadata(base + ".svg")
    plt.close(fig)
    return counts


def main():
    cat, notes = categorize()
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, "fig1_map")
    label = {c: lab for c, lab, _ in CATS}
    with open(base + ".csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jurisdiction", "category", "category_label"])
        for j in sorted(cat):
            w.writerow([j, cat[j], label[cat[j]]])
    counts = draw(cat, base)
    for c, lab, _ in CATS:
        members = sorted(j for j, v in cat.items() if v == c)
        print(f"{c}  {counts[c]:>2}  {lab}: {', '.join(members)}")
    print("total", sum(counts.values()))
    for n in notes:
        print(n)


if __name__ == "__main__":
    main()
