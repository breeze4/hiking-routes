# Fix: CalTopo Extension CSV Header Row Handling

## Context
When pasting CSV output that includes a header row (e.g., `name,lat,lon`), the extension tries to parse it as marker data. `parseFloat("lat")` returns `NaN`, producing an error for line 1. The fix is to detect and skip header rows.

## Change

**File:** `caltopo-extension/popup.js` — `parseCsv()` function (line 40)

At the top of the `for` loop (after the empty-line check on line 47), add a header-skip check: if this is the first non-empty line and the second field parses as `NaN`, treat it as a header row and `continue`. This avoids false positives on actual data while handling the common case of pasted CSV with field names.

## Verification
1. Open the extension on a CalTopo map page
2. Paste CSV with header: `name,lat,lon\nTest,37.5,-111.5` — should show 1 marker, no errors
3. Paste CSV without header: `Test,37.5,-111.5` — should still work
4. Paste CSV with bad data: `Test,abc,def` — should still show an error (not silently skip)
