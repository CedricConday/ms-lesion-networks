"""Atlas network step: which cortical/subcortical region pairs each participant's lesions touch.

Reads ``derivatives/tract_overlap.tsv`` and Yeh's (2022) HCP-1065 tract-to-region
connectome spreadsheets, maps every tract to the region pairs it carries, and scores
each pair with the weight-averaged lesioned share of its tracts (``lesionnet.connectome``
documents the method and why it is a tract -> region-pair mapping rather than a
per-connection estimate). Done for the Brodmann (39 areas per hemisphere) and HCP-MMP
(180 areas per hemisphere) versions of the connectome.

Outputs, all long format:

- ``derivatives/network_participants.tsv``: one row per participant x parcellation;
- ``derivatives/network_regions.tsv``: one row per participant x parcellation x node;
- ``derivatives/network_pairs.tsv``: one row per parcellation x region pair, the
  pair's cohort summary (medians and counts by group).
"""

from pathlib import Path

import pandas as pd

from lesionnet.connectome import (
    disconnection,
    edge_weights,
    node_summary,
    participant_summary,
    read_t2r,
)

ROOT = Path(__file__).resolve().parents[1]

T2R = ROOT / "sourcedata" / "atlas" / "hcp1065" / "t2r"
PARCELLATIONS = {
    "brodmann": (T2R / "tract_to_region_connectome_BM_KL.xlsx", 0),
    "mmp": (T2R / "tract_to_region_connectome_MMP.xlsx", 0),
}
OVERLAP = ROOT / "derivatives" / "tract_overlap.tsv"
OUT = ROOT / "derivatives"
HIT = 0.01  # a pair or node counts as hit at >= 1 % weight-averaged lesioned share


def main():
    overlap = pd.read_csv(OVERLAP, sep="\t")
    demo = overlap[["participant_id", "group", "age", "sex"]].drop_duplicates()
    people, regions, pairs = [], [], []
    for parc, (path, block) in PARCELLATIONS.items():
        weights = edge_weights(read_t2r(path, block))
        mapped = set(weights["tract"])
        per_pair = []
        for sub, grp in overlap.groupby("participant_id", sort=True):
            frac = grp.set_index("tract")["tract_fraction"]
            ml = grp.set_index("tract")["lesion_ml"]
            edges = disconnection(weights, frac)
            people.append({
                "participant_id": sub,
                "parcellation": parc,
                "mapped_lesion_ml": float(ml[ml.index.isin(mapped)].sum()),
                "unmapped_lesion_ml": float(ml[~ml.index.isin(mapped)].sum()),
                **participant_summary(edges, HIT),
            })
            regions.append(node_summary(edges, HIT).assign(participant_id=sub, parcellation=parc))
            per_pair.append(edges.assign(participant_id=sub))
        per_pair = pd.concat(per_pair).merge(demo[["participant_id", "group"]], on="participant_id")
        per_pair["hit"] = per_pair["disconnection"] >= HIT
        keys = ["node_a", "node_b", "weight"]
        cohort = per_pair[keys].drop_duplicates().set_index(keys)
        for group, label in (("patient", "patients"), ("control", "controls")):
            g = per_pair[per_pair["group"] == group].groupby(keys, sort=True)
            cohort[f"{label}_median"] = g["disconnection"].median()
            cohort[f"{label}_hit"] = g["hit"].sum().astype(int)
        pairs.append(cohort.reset_index().assign(parcellation=parc))

    people = pd.DataFrame(people).merge(demo, on="participant_id")
    regions = pd.concat(regions).merge(demo, on="participant_id")
    regions = regions[["participant_id", "parcellation", "node", "node_disconnection",
                       "n_pairs", "n_pairs_hit", "group", "age", "sex"]]
    pairs = pd.concat(pairs)
    pairs = pairs[["parcellation", "node_a", "node_b", "weight", "patients_median",
                   "controls_median", "patients_hit", "controls_hit"]]
    for name, table in (("network_participants", people), ("network_regions", regions),
                        ("network_pairs", pairs)):
        path = OUT / f"{name}.tsv"
        table.to_csv(path, sep="\t", index=False, float_format="%.6g")
        print(f"wrote {path} ({len(table)} rows)")


if __name__ == "__main__":
    main()
