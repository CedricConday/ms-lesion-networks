#!/usr/bin/env bash
# Show LST-AI progress: finished, failed, running and waiting participants.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
done=0; failed=(); waiting=()
running=$(docker ps --filter ancestor=jqmcginnis/lst-ai:v2.0.0rc1-cpu -q | wc -l)
for s in $(tail -n +2 sourcedata/ds007908/participants.tsv | cut -f1); do
  if [ -s "derivatives/lst-ai/$s/space-flair_seg-lst.nii.gz" ]; then
    done=$((done+1))
  elif grep -q "^$s exit=[1-9]" work/logs/batch.log 2>/dev/null; then
    failed+=("$s")
  else
    waiting+=("$s")
  fi
done
echo "$(date '+%F %H:%M')  done $done/28  running $running  failed ${#failed[@]}"
[ ${#failed[@]} -gt 0 ] && echo "failed: ${failed[*]}  (see work/logs/<sub>.log)"
[ "$running" -eq 0 ] && [ ${#waiting[@]} -gt 0 ] && \
  echo "nothing running but ${#waiting[@]} unfinished — run scripts/resume.sh"
grep -h "seconds=" work/logs/batch.log 2>/dev/null | tail -3
