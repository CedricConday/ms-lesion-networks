#!/usr/bin/env bash
# Probe: does LST-AI v2.0.0rc1-cpu (native arm64, no qemu) write the MNI-space segmentation
# that scripts/03_tract_overlap.py reads (work/<sub>/*space-mni_seg-lst.nii.gz)?
# Runs one participant with the study's flags plus --fast-mode for speed, into work/probe/,
# touching nothing the running v1.2.0 batch uses.
# Usage: scripts/probe_lst_v2.sh sub-0422
set -uo pipefail
S=${1:-sub-0422}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG=jqmcginnis/lst-ai:v2.0.0rc1-cpu
IN="$ROOT/sourcedata/ds007908/$S/ses-1/anat"
OUT="$ROOT/work/probe/$S/out"; TMP="$ROOT/work/probe/$S/tmp"; LOG="$ROOT/work/probe/$S.log"
mkdir -p "$OUT" "$TMP"
NAME="probe-lst-v2-$S"; docker rm -f "$NAME" >/dev/null 2>&1
start=$(date +%s)
docker run -d --name "$NAME" -v "$IN":/in:ro -v "$OUT":/out -v "$TMP":/tmpd "$IMG" \
  --t1 "/in/${S}_ses-1_T1w.nii.gz" --flair "/in/${S}_ses-1_FLAIR.nii.gz" \
  --output /out --temp /tmpd --device cpu --threads 4 --fast-mode >/dev/null || { echo "$S start failed"; exit 1; }
rc=$(docker wait "$NAME"); docker logs "$NAME" > "$LOG" 2>&1; docker rm "$NAME" >/dev/null 2>&1
docker run --rm -v "$ROOT":/p --entrypoint chown "$IMG" -R "$(id -u):$(id -g)" "/p/work/probe/$S" >/dev/null 2>&1
echo "$S exit=$rc seconds=$(( $(date +%s) - start ))"
echo "out:"; ls -la "$OUT"; echo "tmp:"; ls -la "$TMP"
echo "MNI seg files: $(ls "$TMP"/*space-mni_seg-lst.nii.gz "$OUT"/*space-mni_seg-lst.nii.gz 2>/dev/null | wc -l)"
