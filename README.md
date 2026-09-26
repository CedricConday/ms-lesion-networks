# ms-lesion-networks

An open, reproducible pipeline that segments white-matter lesions in the public
multiple sclerosis dataset **OpenNeuro ds007908** and measures how much of each
large-scale brain network the lesions overlap.

> **Nothing in this repository is evidence about multiple sclerosis.** It is a
> software pipeline and a description of one small public dataset (20 patients,
> 8 controls, baseline only). It makes no diagnostic or clinical claim.

## Status

Work in progress, started 2026-09-26.

1. Fetch T1w + FLAIR for all 28 participants (`scripts/01_fetch_anat.sh`) — done
2. Lesion segmentation with LST-AI
3. Lesion-to-network overlap with nilearn
4. Figures and write-up

## Data

Kuceyeski A, Jamison KW, Huang K, Kang Y, Hurtado Rua S, George N, Gauthier SA.
*Multi-scale, multi-modal imaging assessment of trajectories of cognitive
impairment in Multiple Sclerosis.* OpenNeuro ds007908, v1.1.0 (2026).
doi:[10.18112/openneuro.ds007908.v1.1.0](https://doi.org/10.18112/openneuro.ds007908.v1.1.0).
CC0. Funded by NIH/NINDS 1R01NS134646. The FLAIR images used here were added in
v1.1.0 (2026-08-17).

The data are not redistributed here; `scripts/01_fetch_anat.sh` downloads them.
