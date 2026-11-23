#!/usr/bin/env bash
# Fetch the HCP-1065 resources (Yeh 2022) this pipeline reads, and check their checksums:
#   sourcedata/atlas/hcp1065/prob/  64 population-probability tract maps (NIfTI, ICBM152 2009a)
#   sourcedata/atlas/hcp1065/t2r/   the tract-to-region connectome spreadsheets
# Source: https://brain.labsolver.org/hcp_trk_atlas.html (CC BY-SA 4.0; HCP data terms apply).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/sourcedata/atlas/hcp1065"
BASE=https://github.com/data-others/atlas/releases/download/hcp1065
mkdir -p "$DIR/t2r" "$DIR/dl"
curl -sfL -o "$DIR/dl/hcp1065_prob_coverage_nifti.zip" "$BASE/hcp1065_prob_coverage_nifti.zip"
for f in tract_to_region_connectome_MMP.xlsx tract_to_region_connectome_BM_KL.xlsx abbreviation2.xlsx; do
  curl -sfL -o "$DIR/t2r/$f" "$BASE/$f"
done
cd "$DIR"
sha256sum -c <<'EOF'
4577abce53e05c732a0d52c88f4ee2d63488bb685f664faad2ea44aa90be8e8b  dl/hcp1065_prob_coverage_nifti.zip
5fc18a1ea5d8891e0a49e3f1d5386f6021eff1ca94f8207908b39bfea0dfb5a7  t2r/tract_to_region_connectome_MMP.xlsx
8baaf81429c563b1043e078c0ed7a521424577287735847d6aa5646aba98ada5  t2r/tract_to_region_connectome_BM_KL.xlsx
7325e06cdca5e36e5ac7719261daee3d11a3a1816f47d42e3e57bc17e35344fb  t2r/abbreviation2.xlsx
EOF
unzip -q -o dl/hcp1065_prob_coverage_nifti.zip -d .
echo "$(ls prob/*.nii.gz | wc -l) tract maps under $DIR/prob"
