"""Atlas-based network estimate from the HCP-1065 tract-to-region connectome.

Resource: Yeh F-C (2022), *Population-based tract-to-region connectome of the human brain
and its hierarchical topology*, Nat Commun 13:4933, doi:10.1038/s41467-022-32595-4. The
published connectome is a matrix of cortical regions x 52 tracts (26 per hemisphere),
each entry the population probability (1065 HCP young adults) that the tract innervates
the region, for the Brodmann, Kleist and HCP-MMP parcellations. Commissural, cerebellar
and brainstem pathways are not in it, and subcortical structures are not rows.

It is a tract-to-region table, not a region-to-region one: it says which cortical regions
a tract reaches, not which of those regions a given streamline joins, nor where along the
tract a lesion sits relative to any one connection. A per-connection disconnection
estimate therefore cannot be read off it. What this module does instead is the documented
fallback, a tract -> region-pair mapping:

- an *association* tract with population probability ``p_i`` at region ``i`` and ``p_j``
  at region ``j`` (same hemisphere) is taken to carry the pair (i, j) with weight
  ``p_i * p_j``. "Carry" means co-innervation, not a verified connection;
- a *projection* tract (corticospinal, corticobulbar, corticostriatal, corticothalamic,
  optic radiation, fornix) carries the pair (cortical region i, the tract's subcortical
  target) with weight ``p_i``. The subcortical targets are a textbook anatomical label
  added here; they are not part of Yeh's matrix;
- entries below 5 % population probability are set to zero. The paper blanks such
  entries in its figures for readability; using it as a floor here is a choice.

For one participant with lesioned share ``f_t`` of tract ``t`` (``tract_fraction`` from
the overlap step), the disconnection of a pair is the weight-averaged lesioned share of
the tracts that carry it::

    D(i, j) = sum_t w_t(i, j) * f_t / sum_t w_t(i, j)

so a pair carried by one tract alone inherits exactly that tract's lesioned share, and a
pair carried by no lesioned tract scores 0. It is an estimate of how much of the pathway
under a pair is lesioned in an atlas brain, not a measurement of anyone's connectivity.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

# Column abbreviations of Yeh's spreadsheets -> stem of the HCP-1065 probability map
# (the map's file name without the _L/_R suffix and .nii.gz).
TRACT_FILES = {
    "FAT": "Frontal_Aslant_Tract",
    "AF": "Arcuate_Fasciculus",
    "PTAT": "Parietal_Aslant_Tract",
    "MdLF": "Middle_Longitudinal_Fasciculus",
    "SLF_III": "Superior_Longitudinal_Fasciculus3",
    "SLF_II": "Superior_Longitudinal_Fasciculus2",
    "SLF_I": "Superior_Longitudinal_Fasciculus1",
    "C_FP": "Cingulum_Frontal_Parietal",
    "C_R": "Cingulum_Rarolfactory",
    "C_FPH": "Cingulum_Frontal_Parahippocampal",
    "C_PHP": "Cingulum_Parahippocampal_Parietal",
    "C_PH": "Cingulum_Parahippocampal",
    "ILF": "Inferior_Longitudinal_Fasciculus",
    "IFOF": "Inferior_Fronto_Occipital_Fasciculus",
    "UF": "Uncinate_Fasciculus",
    "VOF": "Vertical_Occipital_Fasciculus",
    "CST": "Corticospinal_Tract",
    "CBT": "Corticobulbar_Tract",
    "CStr_A": "Corticostriatal_Tract_Anterior",
    "CStr_P": "Corticostriatal_Tract_Posterior",
    "CStr_S": "Corticostriatal_Tract_Superior",
    "CTh_A": "Thalamic_Radiation_Anterior",
    "CTh_P": "Thalamic_Radiation_Posterior",
    "CTh_S": "Thalamic_Radiation_Superior",
    "OR": "Optic_Radiation",
    "F": "Fornix",
}

# Projection tracts: one cortical end in the matrix, the other end subcortical.
PROJECTION_TARGET = {
    "CST": "brainstem_spinal",
    "CBT": "brainstem",
    "CStr_A": "striatum",
    "CStr_P": "striatum",
    "CStr_S": "striatum",
    "CTh_A": "thalamus",
    "CTh_P": "thalamus",
    "CTh_S": "thalamus",
    "OR": "thalamus",
    "F": "mammillary_septal",
}

FLOOR = 0.05


def _region_name(value) -> str:
    """Spreadsheet region labels mix strings and bare numbers (HCP-MMP area 52, 2, 46...)."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def read_t2r(path: Path, block: int = 0) -> pd.DataFrame:
    """Read one tract-to-region matrix from Yeh's spreadsheet into long format.

    ``block`` picks the matrix when a sheet holds several stacked under each other
    (``tract_to_region_connectome_BM_KL.xlsx``: 0 = Brodmann, 1 = Kleist). Each block
    starts at a header row naming the 26 tracts twice, left hemisphere then right.
    Returns columns ``region``, ``hemi`` (L/R), ``abbrev``, ``tract`` (atlas map name)
    and ``p``.
    """
    sheet = pd.read_excel(path, header=None)
    first = next(iter(TRACT_FILES))
    headers = [i for i in range(len(sheet)) if sheet.iat[i, 1] == first]
    if block >= len(headers):
        raise ValueError(f"{path}: {len(headers)} matrix block(s), asked for block {block}")
    start = headers[block] + 1
    stop = headers[block + 1] if block + 1 < len(headers) else len(sheet)
    abbrevs = list(sheet.iloc[headers[block], 1:])
    # Left half then right half. Where the sheet labels the halves (a LEFT/RIGHT row above
    # the header), check that the labels sit where the second run of tract names begins.
    if headers[block] > 0:
        labels = list(sheet.iloc[headers[block] - 1, 1:])
        if "LEFT" in labels or "RIGHT" in labels:
            half = len(abbrevs) // 2
            if labels[0] != "LEFT" or labels[half] != "RIGHT":
                raise ValueError(f"{path}: LEFT/RIGHT labels not at columns 1 and {half + 1}")
    rows = []
    seen: dict[str, int] = {}
    for col, abbrev in enumerate(abbrevs, start=1):
        if abbrev not in TRACT_FILES:
            raise ValueError(f"{path}: unknown tract column {abbrev!r}")
        hemi = "L" if seen.get(abbrev, 0) == 0 else "R"
        seen[abbrev] = seen.get(abbrev, 0) + 1
        for r in range(start, stop):
            region = sheet.iat[r, 0]
            p = sheet.iat[r, col]
            if pd.isna(region) or pd.isna(p):
                continue
            rows.append({
                "region": _region_name(region),
                "hemi": hemi,
                "abbrev": abbrev,
                "tract": f"{TRACT_FILES[abbrev]}_{hemi}",
                "p": float(p),
            })
    if sorted(seen.values()) != [2] * len(TRACT_FILES):
        raise ValueError(f"{path}: expected every tract once per hemisphere, got {seen}")
    return pd.DataFrame(rows)


def edge_weights(t2r: pd.DataFrame, floor: float = FLOOR) -> pd.DataFrame:
    """Map every tract to the region pairs it carries, with the pair's weight.

    Returns columns ``tract``, ``node_a``, ``node_b``, ``weight``; nodes are
    ``<hemi>_<region>`` and ``node_a < node_b``.
    """
    rows = []
    for (tract, abbrev, hemi), grp in t2r.groupby(["tract", "abbrev", "hemi"], sort=True):
        hit = grp[grp["p"] >= floor]
        nodes = [(f"{hemi}_{r}", p) for r, p in zip(hit["region"], hit["p"])]
        if abbrev in PROJECTION_TARGET:
            target = f"{hemi}_{PROJECTION_TARGET[abbrev]}"
            pairs = [(n, target, p) for n, p in nodes]
        else:
            pairs = [(a, b, pa * pb) for (a, pa), (b, pb) in combinations(nodes, 2)]
        for a, b, w in pairs:
            a, b = sorted((a, b))
            rows.append({"tract": tract, "node_a": a, "node_b": b, "weight": w})
    return pd.DataFrame(rows, columns=["tract", "node_a", "node_b", "weight"])


def disconnection(weights: pd.DataFrame, tract_fraction: pd.Series) -> pd.DataFrame:
    """Per-pair disconnection for one participant.

    ``tract_fraction`` is indexed by tract name and must cover every tract in
    ``weights``. Returns ``node_a``, ``node_b``, ``weight`` (summed over tracts) and
    ``disconnection`` (weight-averaged lesioned share of the carrying tracts).
    """
    missing = sorted(set(weights["tract"]) - set(tract_fraction.index))
    if missing:
        raise KeyError(f"no tract_fraction for {missing}")
    w = weights.assign(f=weights["tract"].map(tract_fraction).astype(float))
    w["wf"] = w["weight"] * w["f"]
    out = w.groupby(["node_a", "node_b"], sort=True)[["weight", "wf"]].sum().reset_index()
    out["disconnection"] = out["wf"] / out["weight"]
    return out.drop(columns="wf")


def node_summary(edges: pd.DataFrame, threshold: float = 0.01) -> pd.DataFrame:
    """Per-node summary of one participant's pair disconnections.

    ``node_disconnection`` is the weight-averaged disconnection of every pair the node
    belongs to; ``n_pairs`` counts those pairs and ``n_pairs_hit`` the ones at or above
    ``threshold``.
    """
    half = []
    for col in ("node_a", "node_b"):
        half.append(edges[[col, "weight", "disconnection"]].rename(columns={col: "node"}))
    long = pd.concat(half, ignore_index=True)
    long["wd"] = long["weight"] * long["disconnection"]
    long["hit"] = long["disconnection"] >= threshold
    g = long.groupby("node", sort=True)
    out = pd.DataFrame({
        "node_disconnection": g["wd"].sum() / g["weight"].sum(),
        "n_pairs": g.size(),
        "n_pairs_hit": g["hit"].sum().astype(int),
    }).reset_index()
    return out


def participant_summary(edges: pd.DataFrame, threshold: float = 0.01) -> dict:
    """One-line summary of one participant's pair disconnections."""
    d = edges["disconnection"].to_numpy()
    w = edges["weight"].to_numpy()
    top = edges.iloc[int(np.argmax(d))] if len(d) else None
    return {
        "n_pairs": len(d),
        "n_pairs_any": int((d > 0).sum()),
        "n_pairs_hit": int((d >= threshold).sum()),
        "mean_disconnection": float(np.average(d, weights=w)) if len(d) else 0.0,
        "max_disconnection": float(d.max()) if len(d) else 0.0,
        "max_pair": f"{top['node_a']}--{top['node_b']}" if top is not None and d.max() > 0 else "",
    }
