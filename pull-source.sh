#!/usr/bin/env bash
set -euo pipefail

SOURCES_FILE="input/sources.txt"
OUTPUT_DIR="output/sources"
PROMPT_FILE="input/source-pull-prompt.md"
LOG_DIR=".source-pull-logs"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

# Parse sources.txt: skip header line, extract title and URL from each line
# Format: "Title, accessed Date, URL"
pick_next_source() {
  while IFS= read -r line; do
    [[ "$line" == "Works cited" ]] && continue
    [[ -z "$line" ]] && continue

    # Extract URL (last word — always starts with http)
    url=$(echo "$line" | grep -oP 'https?://\S+$')
    # Extract title (everything before ", accessed")
    title="${line%%, accessed*}"

    # Generate slug from URL
    slug=$(echo "$url" \
      | sed 's|https\?://||; s|www\.||; s|/\?$||' \
      | tr '/' '-' \
      | tr '.' '-' \
      | sed 's|[^a-zA-Z0-9_-]||g' \
      | cut -c1-80)

    # Skip if already pulled
    if [[ -d "$OUTPUT_DIR/$slug" ]] && [[ -f "$OUTPUT_DIR/$slug/content.md" ]]; then
      echo "  SKIP: $slug (already exists)" >&2
      continue
    fi

    # Export as tab-separated
    printf '%s\t%s\t%s\n' "$title" "$url" "$slug"
    return 0
  done < "$SOURCES_FILE"

  return 1
}

# Pick next unprocessed source
echo "Scanning for next unprocessed source..."
next=$(pick_next_source) || { echo "All sources have been processed."; exit 0; }

title=$(printf '%s' "$next" | cut -f1)
url=$(printf '%s' "$next" | cut -f2)
slug=$(printf '%s' "$next" | cut -f3)

echo "Pulling: $title"
echo "    URL: $url"
echo "   Slug: $slug"
echo ""

timestamp=$(date +%Y%m%d-%H%M%S)
logfile="$LOG_DIR/${slug}_${timestamp}.log"

# Build the prompt — use python to safely template since URLs contain special chars
prompt=$(python3 -c "
import sys
tmpl = open('$PROMPT_FILE').read()
print(tmpl
    .replace('{{URL}}', sys.argv[1])
    .replace('{{TITLE}}', sys.argv[2])
    .replace('{{SLUG}}', sys.argv[3])
    .replace('{{OUTPUT_DIR}}', sys.argv[4]))
" "$url" "$title" "$slug" "$OUTPUT_DIR/$slug")

echo "Launching claude..."
echo "Log: $logfile"
echo "---"

claude --permission-mode acceptEdits \
  --allowedTools "Bash(curl:*)" \
  --allowedTools "Bash(mkdir:*)" \
  --allowedTools "Bash(wget:*)" \
  --allowedTools "Bash(file:*)" \
  --allowedTools "Bash(wc:*)" \
  --allowedTools "Bash(ls:*)" \
  --allowedTools "Bash(python3:*)" \
  --allowedTools "Bash(python:*)" \
  --allowedTools "Write" \
  --allowedTools "Read" \
  --allowedTools "Edit" \
  --allowedTools "Glob" \
  --allowedTools "Grep" \
  --allowedTools "WebFetch" \
  --model sonnet \
  -p "$prompt" \
  2>&1 | tee "$logfile"

echo ""
echo "--- Done ---"
echo "Output: $OUTPUT_DIR/$slug/"
ls -la "$OUTPUT_DIR/$slug/" 2>/dev/null || echo "(no output directory created)"
