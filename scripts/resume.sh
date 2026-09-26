#!/usr/bin/env bash
# Re-queue every participant without a finished LST-AI segmentation, 4 at a
# time, detached from the terminal so it survives logout. Refuses to start
# while LST-AI containers are still running.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -n "$(docker ps --filter ancestor=jqmcginnis/lst-ai:v1.2.0 -q)" ]; then
  echo "LST-AI is still running; check scripts/status.sh and try again later." >&2
  exit 1
fi
mkdir -p work/logs
: > work/queue.txt
for s in $(tail -n +2 sourcedata/ds007908/participants.tsv | cut -f1); do
  [ -s "derivatives/lst-ai/$s/space-flair_seg-lst.nii.gz" ] || echo "$s" >> work/queue.txt
done
n=$(wc -l < work/queue.txt)
[ "$n" -eq 0 ] && { echo "all 28 finished"; exit 0; }
nohup sh -c 'xargs -P 4 -n 1 ./scripts/02_run_lst_ai.sh < work/queue.txt >> work/logs/batch.log 2>&1' >/dev/null 2>&1 &
echo "queued $n participant(s), 4 at a time; progress: scripts/status.sh"
