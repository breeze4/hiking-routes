# Add Resources and Trip Reports to Canyoneering Hike Pages

## Context

Hike pages in the canyoneering-app currently only contain book content. We want to add support for external links (trip reports, beta, maps, etc.) that can be associated with each hike. These are added as structured data in YAML front matter and rendered as a section at the bottom of the page.

## Format

In any hike's markdown front matter, add a `resources` list. Each entry supports three forms:

```yaml
resources:
  # Full form: URL + title + notes
  - url: https://example.com/report
    title: Trip Report by John
    notes: Good beta on the exit route

  # URL + title only
  - url: https://example.com/another
    title: Some Resource

  # URL only (displayed as the bare URL)
  - url: https://example.com/bare-link
```

## Changes

### 1. Update `canyoneering-app/build.py` — render resources section

In `discover_pages()`, pass through the `resources` list from front matter into the page dict.

In `build()`, after assembling `full_content` (title heading + markdown HTML), append a rendered resources section if the page has resources. Rendering logic:
- Wrap in a `<div class="resources">` with an `<h3>Resources and Trip Reports</h3>` heading
- Each resource is a list item (`<ul>`)
- If title exists: `<a href="{url}">{title}</a>`
- If no title: `<a href="{url}">{url}</a>`
- If notes exist: append notes text after the link

### 2. Update `canyoneering-app/style.css` — style the resources section

Add styles for `.resources`:
- Visual separator (top border) to distinguish from book content
- Slightly muted styling to indicate supplementary material
- Standard link styling for the URLs

### 3. Update `CLAUDE.md` — document the feature

Add a brief note about the `resources` front matter field in the project structure docs.

## Files Modified

- `canyoneering-app/build.py` — parse and render resources
- `canyoneering-app/style.css` — resources section styling
- `CLAUDE.md` — document the feature

## Verification

1. Add a test `resources` entry to one hike's front matter (e.g., `death-hollow.md`)
2. Run `python3 canyoneering-app/build.py`
3. Open `html/canyoneering-3/death-hollow.html` in browser
4. Verify the resources section appears at the bottom with correct links and styling
5. Verify hike pages without resources are unaffected
