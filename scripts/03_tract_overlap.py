"""Measure how much of each white-matter tract the LST-AI lesions overlap.

For every participant, the MNI-space lesion mask written by LST-AI is resampled
onto the grid of the HCP-1065 population-probability tract atlas (Yeh 2022).
Two numbers are reported per tract:

- ``lesion_ml``: lesion volume inside the tract, weighting each voxel by the
  atlas probability that the tract passes through it (probability-weighted mL);
- ``tract_fraction``: that volume divided by the tract's own probability-weighted
  volume, i.e. the share of the tract that is lesioned.

Output: ``derivatives/tract_overlap.tsv`` (long format, one row per
participant x tract).
"""

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.image import resample_to_img

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


def load_atlas():
    tracts = {}
    for path in sorted(ATLAS_DIR.glob("*.nii.gz")):
        name = path.name.removesuffix(".nii.gz")
        tracts[name] = nib.load(path)
    if not tracts:
        raise FileNotFoundError(f"no tract maps under {ATLAS_DIR}")
    return tracts


def main():
    participants = pd.read_csv(PARTICIPANTS, sep="\t")
    tracts = load_atlas()
    reference = next(iter(tracts.values()))
    voxel_ml = float(np.prod(reference.header.get_zooms()[:3])) / 1000.0
    prob = {name: img.get_fdata(dtype=np.float32) for name, img in tracts.items()}
    tract_ml = {name: p.sum() * voxel_ml for name, p in prob.items()}

    rows = []
    for sub in participants["participant_id"]:
        mask_img = resample_to_img(
            find_mni_lesion_mask(sub), reference,
            interpolation="nearest", copy_header=True, force_resample=True,
        )
        lesion = mask_img.get_fdata() > 0.5
        for name, p in prob.items():
            ml = float(p[lesion].sum()) * voxel_ml
            rows.append({
                "participant_id": sub,
                "tract": name,
                "lesion_ml": ml,
                "tract_fraction": ml / tract_ml[name],
            })

    table = pd.DataFrame(rows).merge(participants, on="participant_id")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, sep="\t", index=False, float_format="%.6g")
    print(f"wrote {OUT} ({len(table)} rows)")


if __name__ == "__main__":
    main()
