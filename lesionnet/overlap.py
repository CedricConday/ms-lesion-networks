"""Lesion-to-tract overlap against a population-probability tract atlas.

Two numbers per tract:

- ``lesion_ml``: lesion volume inside the tract, each lesioned voxel weighted by the
  atlas probability that the tract passes through it (probability-weighted mL);
- ``tract_fraction``: that volume divided by the tract's own probability-weighted
  volume, i.e. the share of the tract that is lesioned.
"""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd


def voxel_ml(img: nib.spatialimages.SpatialImage) -> float:
    """Volume of one voxel of ``img`` in millilitres."""
    return float(np.prod(img.header.get_zooms()[:3])) / 1000.0


def load_atlas(atlas_dir: Path) -> dict[str, nib.Nifti1Image]:
    """Read every ``<tract>.nii.gz`` probability map under ``atlas_dir``, keyed by tract name."""
    tracts = {
        path.name.removesuffix(".nii.gz"): nib.load(path)
        for path in sorted(Path(atlas_dir).glob("*.nii.gz"))
    }
    if not tracts:
        raise FileNotFoundError(f"no tract maps under {atlas_dir}")
    return tracts


def tract_overlap(lesion: np.ndarray, prob: dict[str, np.ndarray], vox_ml: float) -> pd.DataFrame:
    """Overlap of one binary lesion mask with every tract probability map.

    ``lesion`` and each ``prob`` array must share one grid. Returns one row per tract with
    ``tract``, ``lesion_ml`` and ``tract_fraction``. A tract with zero probability mass
    gets a ``tract_fraction`` of 0 rather than a division by zero.
    """
    lesion = np.asarray(lesion, dtype=bool)
    rows = []
    for name, p in prob.items():
        if p.shape != lesion.shape:
            raise ValueError(f"{name}: atlas grid {p.shape} != lesion grid {lesion.shape}")
        ml = float(p[lesion].sum()) * vox_ml
        total = float(p.sum()) * vox_ml
        rows.append({
            "tract": name,
            "lesion_ml": ml,
            "tract_fraction": ml / total if total > 0 else 0.0,
        })
    return pd.DataFrame(rows)
