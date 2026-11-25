#!/usr/bin/env bash
# Stop every Daily draft / Approve-and-publish run that is still waiting for your Approve tap.
# Why: a tap publishes the draft file THAT RUN checked out when it started. After a LinkedIn redo such a run would still hold the old text, so it must end before the new text is saved.
# A cancelled run still saves its state on the way out, so this waits until they have really finished (the new text is written only after that).
set -u
REPO="${GITHUB_REPOSITORY:?}"
WORKFLOWS="daily-draft.yml approve-publish.yml"
for wf in $WORKFLOWS; do
  for st in in_progress queued; do
    for id in $(gh run list -R "$REPO" --workflow "$wf" --status "$st" --json databaseId --jq '.[].databaseId'); do
      echo "stopping $wf run $id ($st)"
      gh run cancel -R "$REPO" "$id" || true
    done
  done
done
for i in $(seq 1 36); do
  n=0
  for wf in $WORKFLOWS; do
    c=$(gh run list -R "$REPO" --workflow "$wf" --status in_progress --json databaseId --jq 'length')
    n=$((n + ${c:-0}))
  done
  if [ "$n" -eq 0 ]; then echo "no listener is running"; exit 0; fi
  sleep 10
done
echo "::error::old runs did not stop within 6 minutes"
exit 1
