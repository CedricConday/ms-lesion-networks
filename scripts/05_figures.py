"""Figures for the README, each rendered for a light and a dark page.

1. ``figures/load_<theme>.svg``: per-participant total in-tract lesion load, by group;
2. ``figures/heatmap_<theme>.svg``: lesioned share of every tract x participant;
3. ``figures/network_<theme>.svg``: Brodmann-area pairs hit (weight-averaged disconnection
   >= 1 %) in at least half of the patients (from ``derivatives/network_pairs.tsv``).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, PowerNorm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "derivatives"
FIG = ROOT / "figures"

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", patient="#2a78d6", control="#eb6834",
                  ramp=["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                 grid="#2c2c2a", patient="#3987e5", control="#d95926",
                 ramp=["#1a1a19", "#104281", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb"]),
}


def display(tract):
    """Tract label for figures; the atlas file name misspells the parolfactory cingulum."""
    return tract.replace("Rarolfactory", "Parolfactory").replace("_", " ")


def style(t):
    plt.rcParams.update({
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"],
        "savefig.facecolor": t["surface"], "text.color": t["ink"],
        "axes.labelcolor": t["ink2"], "axes.edgecolor": t["muted"],
        "xtick.color": t["ink2"], "ytick.color": t["ink2"], "font.size": 9,
        "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none",
        "font.family": "DejaVu Sans", "svg.hashsalt": "ms-lesion-networks",
    })


def load_figure(overlap, t, out):
    total = overlap.groupby(["participant_id", "group"])["lesion_ml"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    rng = np.random.default_rng(0)
    for x, (group, label) in enumerate((("patient", "Patients"), ("control", "Controls"))):
        v = total.loc[total.group == group, "lesion_ml"].to_numpy()
        jitter = rng.uniform(-0.12, 0.12, len(v))
        ax.scatter(x + jitter, v, s=36, color=t[group], edgecolor=t["surface"], linewidth=1.5, zorder=3)
        med = np.median(v)
        ax.plot([x - 0.25, x + 0.25], [med, med], color=t["ink"], linewidth=2, zorder=4)
        ax.annotate(f"median {med:.2g} ml", (x + 0.28, med), va="center", fontsize=8, color=t["ink2"])
        ax.annotate(f"{label}\nn = {len(v)}", (x, -0.16), xycoords=("data", "axes fraction"),
                    ha="center", va="top", color=t["ink"])
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_ylim(-0.002, 150)
    ax.set_yticks([0, 0.01, 0.1, 1, 10, 100])
    ax.set_yticklabels(["0", "0.01", "0.1", "1", "10", "100"])
    ax.set_xlim(-0.6, 1.9)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.grid(axis="y", color=t["grid"], linewidth=0.6, zorder=0)
    ax.set_ylabel("Summed tract overlap, probability-weighted ml\n"
                  "(sum over 64 overlapping tracts, not a lesion volume; symlog)")
    ax.set_title("Summed lesion-tract overlap per participant", loc="left", fontsize=10, color=t["ink"])
    fig.subplots_adjust(left=0.2, bottom=0.16, top=0.92, right=0.97)
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def heatmap_figure(overlap, t, out):
    wide = overlap.pivot(index="tract", columns="participant_id", values="tract_fraction") * 100
    group = overlap.drop_duplicates("participant_id").set_index("participant_id")["group"]
    total = overlap.groupby("participant_id")["lesion_ml"].sum()
    order = sorted(wide.columns, key=lambda s: (group[s] != "patient", -total[s]))
    pats = [s for s in order if group[s] == "patient"]
    tracts = wide[pats].median(axis=1).sort_values(ascending=False).index
    wide = wide.loc[tracts, order]
    cmap = LinearSegmentedColormap.from_list("seq", t["ramp"])
    fig, ax = plt.subplots(figsize=(8.2, 11.5))
    im = ax.imshow(wide.to_numpy(), aspect="auto", cmap=cmap,
                   norm=PowerNorm(gamma=0.4, vmin=0, vmax=max(5.0, float(wide.to_numpy().max()))),
                   interpolation="nearest")
    ax.set_yticks(range(len(tracts)))
    ax.set_yticklabels([display(s) for s in tracts], fontsize=6.5)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([s.removeprefix("sub-") for s in order], rotation=90, fontsize=6.5)
    for lab, s in zip(ax.get_xticklabels(), order, strict=True):
        lab.set_color(t[group[s]])
    ax.axvline(len(pats) - 0.5, color=t["ink"], linewidth=1.2)
    ax.set_xlabel("Participant (patients left, sorted by total in-tract load; controls right)")
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Lesioned share of the tract, % (power scale)")
    cb.outline.set_visible(False)
    ax.set_title("Lesioned share of each HCP-1065 tract, per participant", loc="left",
                 fontsize=10, color=t["ink"])
    fig.subplots_adjust(left=0.3, right=0.9, top=0.96, bottom=0.08)
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def _node_order(nodes):
    """Brodmann areas by number, subcortical targets last; one list per hemisphere."""
    def key(n):
        name = n[2:]
        if name.startswith("BA"):
            return (0, int(name[2:].split("/")[0]), name)
        return (1, 0, name)
    return sorted(nodes, key=key)


def network_figure(pairs, regions, t, out):
    p = pairs[pairs.parcellation == "brodmann"]
    n_pat = int(regions.loc[regions.group == "patient", "participant_id"].nunique())
    shown = p[p.patients_hit >= n_pat / 2]
    nodes = sorted(set(p.node_a) | set(p.node_b))
    left = _node_order([n for n in nodes if n.startswith("L_")])
    right = _node_order([n for n in nodes if n.startswith("R_")])
    pos = {}
    for side, ns in ((-1, left), (1, right)):
        angles = np.linspace(np.pi * 0.56, np.pi * 1.44, len(ns)) if side < 0 else \
            np.linspace(np.pi * 0.44, -np.pi * 0.44, len(ns))
        for n, a in zip(ns, angles, strict=True):
            pos[n] = (np.cos(a), np.sin(a), a)
    med = (regions[(regions.parcellation == "brodmann") & (regions.group == "patient")]
           .groupby("node")["node_disconnection"].median() * 100)
    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    for _, e in shown.sort_values("patients_hit").iterrows():
        (x0, y0, _), (x1, y1, _) = pos[e.node_a], pos[e.node_b]
        verts = np.array([[x0, y0], [0.3 * (x0 + x1), 0.3 * (y0 + y1)], [x1, y1]])
        tt = np.linspace(0, 1, 30)[:, None]
        curve = (1 - tt) ** 2 * verts[0] + 2 * (1 - tt) * tt * verts[1] + tt ** 2 * verts[2]
        ax.plot(curve[:, 0], curve[:, 1], color=t["patient"], alpha=0.7,
                linewidth=1.2, solid_capstyle="round", zorder=2)
    cmap = LinearSegmentedColormap.from_list("seq", t["ramp"][1:])
    vmax = max(float(med.max()), 1.0)
    for n, (x, y, a) in pos.items():
        v = float(med.get(n, 0.0))
        ax.scatter([x], [y], s=60, color=cmap(min(v / vmax, 1.0) ** 0.6), edgecolor=t["muted"],
                   linewidth=0.6, zorder=3)
        label = n[2:].replace("_", " ")
        deg = np.degrees(a)
        flip = np.cos(a) < 0
        ax.text(1.07 * x, 1.07 * y, label, fontsize=6.5, color=t["ink2"],
                rotation=deg + (180 if flip else 0), rotation_mode="anchor",
                ha="right" if flip else "left", va="center")
    ax.text(-1.0, 1.3, "Left hemisphere", ha="center", color=t["ink"], fontsize=9)
    ax.text(1.0, 1.3, "Right hemisphere", ha="center", color=t["ink"], fontsize=9)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.68, 1.42)
    ax.set_aspect("equal")
    ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=PowerNorm(gamma=0.6, vmin=0, vmax=vmax))
    cax = fig.add_axes([0.32, 0.045, 0.36, 0.014])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("Node colour: patient median node disconnection, %")
    cb.outline.set_visible(False)
    ax.set_title(
        f"Brodmann-area pairs with weight-averaged disconnection ≥ 1 % in at least half of the "
        f"{n_pat} patients\n({len(shown)} of {len(p)} pairs; most patients for any pair: "
        f"{int(p.patients_hit.max())}). Atlas estimate, not measured connectivity.",
        loc="left", fontsize=9, color=t["ink"])
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.02)
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)


def main():
    overlap = pd.read_csv(DER / "tract_overlap.tsv", sep="\t")
    pairs = pd.read_csv(DER / "network_pairs.tsv", sep="\t")
    regions = pd.read_csv(DER / "network_regions.tsv", sep="\t")
    FIG.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        style(t)
        load_figure(overlap, t, FIG / f"load_{name}.svg")
        heatmap_figure(overlap, t, FIG / f"heatmap_{name}.svg")
        network_figure(pairs, regions, t, FIG / f"network_{name}.svg")
    print(f"wrote figures under {FIG}")


if __name__ == "__main__":
    main()
