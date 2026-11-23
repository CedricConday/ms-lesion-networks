"""Measure how much of each white-matter tract the LST-AI lesions overlap.

For every participant, the MNI-space lesion mask written by LST-AI is resampled
onto the grid of the HCP-1065 population-probability tract atlas (Yeh 2022) and
compared with each tract map (see ``lesionnet.overlap`` for the two numbers).

Output: ``derivatives/tract_overlap.tsv`` (long format, one row per
participant x tract).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from nilearn.image import resample_to_img

from lesionnet.overlap import load_atlas, tract_overlap, voxel_ml

ROOT = Path(__file__).resolve().parents[1]

ATLAS_DIR = ROOT / "sourcedata" / "atlas" / "hcp1065" / "prob"
WORK = ROOT / "work"
PARTICIPANTS = ROOT / "sourcedata" / "ds007908" / "participants.tsv"
OUT = ROOT / "derivatives" / "tract_overlap.tsv"


def find_mni_lesion_mask(sub):
    """Return the binary MNI-space lesion segmentation LST-AI left in work/<sub>."""
    hits = sorted((WORK / sub).glob("*space-mni_seg-lst.nii.gz"))
    if len(hits) != 1:
        raise FileNotFoundError(f"{sub}: expected one MNI lesion mask, found {hits}")
    return hits[0]


def main():
    participants = pd.read_csv(PARTICIPANTS, sep="\t")
    tracts = load_atlas(ATLAS_DIR)
    reference = next(iter(tracts.values()))
    prob = {name: img.get_fdata(dtype=np.float32) for name, img in tracts.items()}

    tables = []
    for sub in participants["participant_id"]:
        mask_img = resample_to_img(
            find_mni_lesion_mask(sub), reference,
            interpolation="nearest", copy_header=True, force_resample=True,
        )
        table = tract_overlap(mask_img.get_fdata() > 0.5, prob, voxel_ml(reference))
        tables.append(table.assign(participant_id=sub))

    table = pd.concat(tables, ignore_index=True)
    table = table[["participant_id", "tract", "lesion_ml", "tract_fraction"]]
    table = table.merge(participants, on="participant_id")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, sep="\t", index=False, float_format="%.6g")
    print(f"wrote {OUT} ({len(table)} rows)")


if __name__ == "__main__":
    main()
