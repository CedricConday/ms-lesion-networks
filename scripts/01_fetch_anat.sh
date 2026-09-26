#!/usr/bin/env bash
# Fetch the T1w + FLAIR images (and BIDS top-level metadata) of OpenNeuro ds007908.
# Only anat/ is needed for lesion segmentation; func/dwi/perf are skipped.
set -euo pipefail
DS=ds007908
OUT="$(cd "$(dirname "$0")/.." && pwd)/sourcedata/$DS"
BASE="https://s3.amazonaws.com/openneuro.org"
mkdir -p "$OUT"
for f in dataset_description.json participants.tsv participants.json README CHANGES; do
  curl -sfL "$BASE/$DS/$f" -o "$OUT/$f"
done
tail -n +2 "$OUT/participants.tsv" | cut -f1 | while read -r sub; do
  keys=$(curl -sf "$BASE?list-type=2&prefix=$DS/$sub/" | grep -o '<Key>[^<]*/anat/[^<]*</Key>' | sed 's/<[^>]*>//g')
  for k in $keys; do
    dest="$OUT/${k#$DS/}"
    [ -s "$dest" ] && continue
    mkdir -p "$(dirname "$dest")"
    curl -sfL "$BASE/$k" -o "$dest"
  done
  echo "$sub done"
done
