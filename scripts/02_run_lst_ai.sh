#!/usr/bin/env bash
# Run LST-AI v1.2.0 (Docker, CPU) on one participant of ds007908.
# Usage: scripts/02_run_lst_ai.sh sub-XXXX
# The container runs as root because the image keeps its HD-BET weights in
# /root with mode 0600; outputs are chowned back to the calling user.
set -uo pipefail
S=$1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG=jqmcginnis/lst-ai:v1.2.0
IN="$ROOT/sourcedata/ds007908/$S/ses-1/anat"
OUT="$ROOT/derivatives/lst-ai/$S"
WORK="$ROOT/work/$S"
LOG="$ROOT/work/logs/$S.log"
mkdir -p "$OUT" "$WORK" "$ROOT/work/logs"
start=$(date +%s)
docker run --rm --platform linux/amd64 \
  -v "$IN":/in:ro -v "$OUT":/out -v "$WORK":/tmpd "$IMG" \
  --t1 "/in/${S}_ses-1_T1w.nii.gz" --flair "/in/${S}_ses-1_FLAIR.nii.gz" \
  --output /out --temp /tmpd --device cpu > "$LOG" 2>&1
rc=$?
docker run --rm --platform linux/amd64 -v "$ROOT":/p --entrypoint chown "$IMG" \
  -R "$(id -u):$(id -g)" "/p/work/$S" "/p/derivatives/lst-ai/$S" >/dev/null 2>&1
echo "$S exit=$rc seconds=$(( $(date +%s) - start ))"
