#!/usr/bin/env bash
# Run LST-AI v2.0.0rc1 (CPU image, native arm64) on one participant of ds007908.
# Usage: scripts/02_run_lst_ai.sh sub-XXXX
# Segment-only (no FastSurfer annotation): the downstream step reads the MNI-space
# segmentation LST-AI leaves in work/<sub>/, and the FLAIR-space one lands in
# derivatives/lst-ai/<sub>/. The container runs detached so it survives the calling
# shell; the log is copied out when it exits. The image runs as root and keeps its
# HD-BET weights in /root; outputs are chowned back to the calling user.
set -uo pipefail
S=$1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG=jqmcginnis/lst-ai:v2.0.0rc1-cpu
IN="$ROOT/sourcedata/ds007908/$S/ses-1/anat"
OUT="$ROOT/derivatives/lst-ai/$S"
WORK="$ROOT/work/$S"
LOG="$ROOT/work/logs/$S.log"
mkdir -p "$OUT" "$WORK" "$ROOT/work/logs"
NAME="lst-ai-$S"
docker rm -f "$NAME" >/dev/null 2>&1
start=$(date +%s)
docker run -d --name "$NAME" \
  -v "$IN":/in:ro -v "$OUT":/out -v "$WORK":/tmpd "$IMG" \
  --t1 "/in/${S}_ses-1_T1w.nii.gz" --flair "/in/${S}_ses-1_FLAIR.nii.gz" \
  --output /out --temp /tmpd --device cpu --segment_only --threads 4 >/dev/null \
  || { echo "$S exit=start-failed seconds=0"; exit 1; }
rc=$(docker wait "$NAME")
docker logs "$NAME" > "$LOG" 2>&1
docker rm "$NAME" >/dev/null 2>&1
docker run --rm -v "$ROOT":/p --entrypoint chown "$IMG" \
  -R "$(id -u):$(id -g)" "/p/work/$S" "/p/derivatives/lst-ai/$S" >/dev/null 2>&1
echo "$S exit=$rc seconds=$(( $(date +%s) - start ))"
