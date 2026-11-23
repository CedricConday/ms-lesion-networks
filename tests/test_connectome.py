import numpy as np
import pandas as pd
import pytest

from lesionnet.connectome import (
    TRACT_FILES,
    disconnection,
    edge_weights,
    node_summary,
    participant_summary,
    read_t2r,
)
from lesionnet.overlap import tract_overlap

ABBREVS = list(TRACT_FILES)
REGIONS = ["r1", "r2", "r3", "r4", 52]          # a bare number, as in the HCP-MMP sheet


def write_sheet(path, entries, blocks=1):
    """Write a spreadsheet laid out like Yeh's: a LEFT/RIGHT row, a header row naming the
    26 tracts twice, then one row per region. ``entries`` maps (region, hemi, abbrev) -> p."""
    rows = []
    for b in range(blocks):
        rows.append([None, "LEFT"] + [None] * 25 + ["RIGHT"] + [None] * 25)
        rows.append([None] + ABBREVS + ABBREVS)
        for region in REGIONS:
            row = [region]
            for hemi in ("L", "R"):
                row += [entries.get((str(region), hemi, a), 0.0) * (b + 1) for a in ABBREVS]
            rows.append(row)
        rows.append([None] * 53)
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def t2r_frame(entries):
    rows = []
    for region in map(str, REGIONS):
        for hemi in ("L", "R"):
            for a in ABBREVS:
                rows.append({"region": region, "hemi": hemi, "abbrev": a,
                             "tract": f"{TRACT_FILES[a]}_{hemi}",
                             "p": entries.get((region, hemi, a), 0.0)})
    return pd.DataFrame(rows)


def test_read_t2r_parses_hemispheres_numbers_and_blocks(tmp_path):
    path = tmp_path / "t2r.xlsx"
    write_sheet(path, {("r1", "L", "AF"): 0.4, ("52", "R", "CST"): 0.25}, blocks=2)
    first = read_t2r(path, block=0)
    assert len(first) == len(REGIONS) * 52
    p = first.set_index(["region", "hemi", "abbrev"])["p"]
    assert p[("r1", "L", "AF")] == pytest.approx(0.4)
    assert p[("r1", "R", "AF")] == 0.0
    assert p[("52", "R", "CST")] == pytest.approx(0.25)
    assert set(first.loc[first.abbrev == "AF", "tract"]) == {"Arcuate_Fasciculus_L", "Arcuate_Fasciculus_R"}
    second = read_t2r(path, block=1).set_index(["region", "hemi", "abbrev"])["p"]
    assert second[("r1", "L", "AF")] == pytest.approx(0.8)
    with pytest.raises(ValueError):
        read_t2r(path, block=2)


def test_association_tract_carries_all_pairs_of_its_regions():
    w = edge_weights(t2r_frame({("r1", "L", "AF"): 1.0, ("r2", "L", "AF"): 0.5,
                                ("r3", "L", "AF"): 0.04}))   # below the 5 % floor
    assert len(w) == 1
    row = w.iloc[0]
    assert (row.node_a, row.node_b, row.tract) == ("L_r1", "L_r2", "Arcuate_Fasciculus_L")
    assert row.weight == pytest.approx(0.5)


def test_projection_tract_pairs_cortex_with_its_subcortical_target():
    w = edge_weights(t2r_frame({("r1", "R", "CST"): 0.9, ("r2", "R", "CST"): 0.6,
                                ("r3", "L", "CTh_A"): 1.0}))
    pairs = {(a, b): x for a, b, x in zip(w.node_a, w.node_b, w.weight)}
    assert pairs == {
        ("R_brainstem_spinal", "R_r1"): pytest.approx(0.9),
        ("R_brainstem_spinal", "R_r2"): pytest.approx(0.6),
        ("L_r3", "L_thalamus"): pytest.approx(1.0),
    }


def test_disconnection_is_the_weighted_mean_over_carrying_tracts():
    # r1-r2 is carried by AF (weight 1.0) and by ILF (weight 0.25)
    w = edge_weights(t2r_frame({("r1", "L", "AF"): 1.0, ("r2", "L", "AF"): 1.0,
                                ("r1", "L", "ILF"): 0.5, ("r2", "L", "ILF"): 0.5}))
    frac = pd.Series({"Arcuate_Fasciculus_L": 0.2, "Inferior_Longitudinal_Fasciculus_L": 0.0})
    e = disconnection(w, frac)
    assert len(e) == 1
    assert e.weight.iloc[0] == pytest.approx(1.25)
    assert e.disconnection.iloc[0] == pytest.approx(0.2 * 1.0 / 1.25)


def test_missing_tract_fraction_is_an_error():
    w = edge_weights(t2r_frame({("r1", "L", "AF"): 1.0, ("r2", "L", "AF"): 1.0}))
    with pytest.raises(KeyError):
        disconnection(w, pd.Series({"Uncinate_Fasciculus_L": 0.1}))


def test_planted_lesion_disconnects_exactly_the_planted_pair():
    """End to end on synthetic volumes: a lesion fully inside the synthetic arcuate gives
    tract_fraction = its share of that tract and disconnects r1-r2 and nothing else."""
    shape = (12, 12, 12)
    af = np.zeros(shape, np.float32)
    af[1:11, 1:3, 1:3] = 1.0                       # 40 voxels
    ilf = np.zeros(shape, np.float32)
    ilf[1:11, 8:10, 8:10] = 1.0
    prob = {"Arcuate_Fasciculus_L": af, "Inferior_Longitudinal_Fasciculus_L": ilf}
    lesion = np.zeros(shape, bool)
    lesion[2:6, 1:3, 1:3] = True                   # 16 voxels, all inside the arcuate

    overlap = tract_overlap(lesion, prob, vox_ml=0.001).set_index("tract")
    assert overlap.loc["Arcuate_Fasciculus_L", "tract_fraction"] == pytest.approx(16 / 40)
    assert overlap.loc["Inferior_Longitudinal_Fasciculus_L", "tract_fraction"] == 0.0

    t2r = t2r_frame({("r1", "L", "AF"): 1.0, ("r2", "L", "AF"): 1.0,
                     ("r3", "L", "ILF"): 1.0, ("r4", "L", "ILF"): 1.0})
    edges = disconnection(edge_weights(t2r), overlap["tract_fraction"])
    hit = edges[edges.disconnection > 0]
    assert list(zip(hit.node_a, hit.node_b)) == [("L_r1", "L_r2")]
    assert hit.disconnection.iloc[0] == pytest.approx(16 / 40)
    assert edges.set_index(["node_a", "node_b"]).loc[("L_r3", "L_r4"), "disconnection"] == 0.0

    nodes = node_summary(edges).set_index("node")
    assert nodes.loc["L_r1", "node_disconnection"] == pytest.approx(0.4)
    assert nodes.loc["L_r3", "node_disconnection"] == 0.0
    assert nodes.loc["L_r1", "n_pairs_hit"] == 1

    summary = participant_summary(edges)
    assert summary["n_pairs"] == 2
    assert summary["n_pairs_hit"] == 1
    assert summary["max_pair"] == "L_r1--L_r2"
    assert summary["max_disconnection"] == pytest.approx(0.4)
    assert summary["mean_disconnection"] == pytest.approx(0.2)
