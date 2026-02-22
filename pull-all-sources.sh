#!/usr/bin/env bash
set -euo pipefail

count=0
total=$(grep -c 'https\?://' input/sources.txt || true)

echo "=== Pull All Sources ==="
echo "Total sources: $total"
echo ""

while true; do
  count=$((count + 1))
  echo "=========================================="
  echo "  Run #$count"
  echo "=========================================="

  # Run pull-source.sh, capture exit code
  if ! ./pull-source.sh; then
    echo ""
    echo "pull-source.sh exited with error. Stopping."
    break
  fi

  # Check if pull-source.sh reported all done (it prints this and exits 0)
  # Re-run the source picker to see if anything is left
  remaining=$(grep -c 'https\?://' input/sources.txt || true)
  done_count=$(find output/sources -name content.md 2>/dev/null | wc -l)

  echo ""
  echo "Progress: $done_count / $total sources complete"
  echo ""

  if [[ "$done_count" -ge "$total" ]]; then
    echo "=== All $total sources processed. ==="
    break
  fi

  # Brief pause between runs
  sleep 2
done
