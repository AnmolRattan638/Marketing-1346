#!/usr/bin/env bash
# Save bot-owned files (data/) to the repo. Survives concurrent pushes: on conflict our fresh data wins.
set -u
msg="${1:-state}"
git config user.name "marketing-bot"
git config user.email "marketing-bot@users.noreply.github.com"
git add -A data
git diff --cached --quiet && { echo "nothing to save"; exit 0; }
git commit -q -m "$msg"
for i in 1 2 3 4 5; do
  if git pull --rebase -X theirs -q && git push -q; then
    echo "state saved"; exit 0
  fi
  git rebase --abort 2>/dev/null
  sleep $((i * 3))
done
echo "::error::could not save state to the repo"
exit 1
