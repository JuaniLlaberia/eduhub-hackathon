#!/bin/sh
# Manual check of stage 11 (creator brief) with the real model: insights + drafts for one account and one brief.
# Usage (from the repo root): sh src/ai/scripts/brief_check.sh [account] [brief]
#   defaults: paulina_cocina, paulina_cocina_sell
set -e
ACCOUNT="${1:-paulina_cocina}"
BRIEF="${2:-paulina_cocina_sell}"
SNAPSHOT="src/ai/tests/data/real/${ACCOUNT}.json"
BRIEF_FILE="src/ai/scripts/briefs/${BRIEF}.json"
set -a
. ./.env
set +a
echo "=== INSIGHTS: ${ACCOUNT} with brief ${BRIEF} ==="
.venv/bin/python src/ai/scripts/write_insights.py "$SNAPSHOT" --brief "$BRIEF_FILE"
echo
echo "=== DRAFTS: ${ACCOUNT} with brief ${BRIEF} ==="
.venv/bin/python src/ai/scripts/generate_drafts.py "$SNAPSHOT" 3 --brief "$BRIEF_FILE"
