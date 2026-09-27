# ms-lesion-networks

An open, reproducible pipeline that segments white-matter lesions in the public
multiple sclerosis dataset **OpenNeuro ds007908** and measures how much of each
major white-matter tract the lesions overlap.

> **Nothing in this repository is evidence about multiple sclerosis.** It is a
> software pipeline and a description of one small public dataset (20 patients,
> 8 controls, baseline only). It makes no diagnostic or clinical claim.

## Status (2026-09-27)

1. Fetch T1w + FLAIR for all 28 participants (`scripts/01_fetch_anat.sh`): done.
2. Lesion segmentation with LST-AI v2.0.0rc1 (`scripts/02_run_lst_ai.sh`, `resume.sh`,
   `status.sh`): done for 28 of 28, 12 to 14 minutes per participant on four CPU threads.
3. Lesion-to-tract overlap against the HCP-1065 population tract atlas
   (`scripts/03_tract_overlap.py`): done, `derivatives/tract_overlap.tsv`.
4. Figures and write-up: not started.

## What was measured

For every participant, LST-AI's MNI-space lesion mask is resampled onto the grid of
the HCP-1065 population-probability tract atlas (Yeh 2022, 64 tracts). Two numbers per
tract:

- `lesion_ml`: lesion volume inside the tract, each voxel weighted by the atlas
  probability that the tract passes through it;
- `tract_fraction`: that volume divided by the tract's own probability-weighted volume,
  the share of the tract that is lesioned.

The table is long format, one row per participant and tract (28 × 64 = 1,792 rows),
with the group, age and sex columns from `participants.tsv`.

## First numbers, stated as what they are

Summed over all 64 tracts, patients (n = 20) carry 0.04 to 70.4 ml of lesion inside
tracts, median 7.1 ml, and eight of them more than 10 ml. Controls (n = 8) carry 0 to
1.5 ml, median 0.07 ml; two controls have no lesion voxel in any tract. The segmenter
therefore reports something on most controls too, which is a property of the segmenter
on this data (see the bidsgate result below), not a finding about the controls.

The tracts with the highest median lesioned share among patients, with the number of
patients in whom more than 1 % of the tract is lesioned:

| Tract | Patient median share | Control median | Patients > 1 % |
|---|---|---|---|
| Cingulum frontal-parietal L | 0.99 % | 0.000 % | 10 of 20 |
| Corticostriatal tract posterior R | 0.83 % | 0.000 % | 9 of 20 |
| Corticopontine tract parietal R | 0.79 % | 0.000 % | 9 of 20 |
| Arcuate fasciculus R | 0.71 % | 0.000 % | 9 of 20 |
| Corticopontine tract occipital R | 0.63 % | 0.004 % | 7 of 20 |
| Thalamic radiation posterior R | 0.61 % | 0.000 % | 9 of 20 |
| Corticostriatal tract anterior L | 0.61 % | 0.002 % | 6 of 20 |
| Middle longitudinal fasciculus R | 0.61 % | 0.000 % | 9 of 20 |

These are descriptive numbers from one segmenter on 28 people. They are not tested,
not corrected, and not compared with anything. The periventricular tracts dominating
the list is what the anatomy of MS lesions would predict, which is the least
interesting thing a number can be; the per-participant spread (0.04 to 70 ml) is the
thing to look at next.

## How much to trust the segmenter on this data

The same LST-AI image was run through [bidsgate](https://github.com/CedricConday/bidsgate)
on six of these controls with twelve synthetic lesions injected each: it found 64 of 72
(mean Dice 0.82), and seven of the eight misses were among the lowest-placed lesions in
their subject, at cerebellum and brainstem level. Extra components on controls ranged
from 2 to 32 per subject. Read the tract numbers with that in mind: supratentorial
tracts are well covered, infratentorial ones less so, and small control volumes may be
real incidental hyperintensities or segmenter noise; the gate cannot tell.

## Reproduce

```bash
scripts/01_fetch_anat.sh            # T1w + FLAIR for 28 participants from OpenNeuro
scripts/resume.sh                    # LST-AI v2 on every participant without a result, detached
scripts/status.sh                    # done / running / failed
python scripts/03_tract_overlap.py   # derivatives/tract_overlap.tsv
```

Needs Docker (the `jqmcginnis/lst-ai:v2.0.0rc1-cpu` image runs natively on arm64 and
amd64; the older v1.2.0 image is amd64-only and does not finish under emulation) and the
HCP-1065 probability maps under `sourcedata/atlas/hcp1065/prob/`.

## Data

Kuceyeski A, Jamison KW, Huang K, Kang Y, Hurtado Rua S, George N, Gauthier SA.
*Multi-scale, multi-modal imaging assessment of trajectories of cognitive
impairment in Multiple Sclerosis.* OpenNeuro ds007908, v1.1.0 (2026).
doi:[10.18112/openneuro.ds007908.v1.1.0](https://doi.org/10.18112/openneuro.ds007908.v1.1.0).
CC0. Funded by NIH/NINDS 1R01NS134646. The FLAIR images used here were added in
v1.1.0 (2026-08-17). Tract atlas: Yeh F-C, *Population-based tract-to-region
connectome of the human brain and its hierarchical topology*, Nat Commun 2022 (HCP-1065).

The data are not redistributed here; `scripts/01_fetch_anat.sh` downloads them.
`derivatives/tract_overlap.tsv` is derived from public data and carries no images.

MIT. Written by Cedric Conday with Claude (Anthropic) as coding partner.
