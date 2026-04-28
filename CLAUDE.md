# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A static, client-side web app that turns SSA baby-name records (1880–present) into a "vital-signs" report for any American name: peak year, trajectory, all-time count, and a status verdict (Rising / Stable / Declining / Endangered / Extinct). No backend, no tracking, no npm — everything is browser-side against pre-built JSON shards.

## Build Commands

Run from the project root. No npm, no virtual environment needed for the primary path.

```bash
# Rebuild JSON data shards and landing datasets
python3 scripts/build_data.py

# Generate ~2,000 SEO pages + sitemap.xml + robots.txt
python3 scripts/build_pages.py
```

To refresh the SSA source data first:

```bash
curl -fsSL -o /tmp/names.zip https://www.ssa.gov/oact/babynames/names.zip
unzip -o /tmp/names.zip -d data_src
find data_src -type f ! -name 'yob*.txt' -delete
python3 scripts/build_data.py && python3 scripts/build_pages.py
```

## Testing

No automated test suite. Manual verification:

1. Run both build scripts and confirm counts print to stderr without errors.
2. Open `index.html` in a browser; search names and verify reports, sparklines, and share-card download.
3. Open `extinct.html`, `endangered.html`, `rising.html` and verify tables populate.
4. Check a generated `name/<Name>/index.html` to confirm relative asset links resolve.

## Architecture

**Data pipeline (Python → static JSON):**

- `scripts/build_data.py` reads `data_src/yob*.txt` (or fallback `.rda`) and writes:
  - `data/names/<A-Z>.json` — per-letter shards, each with `ym`, `yM`, and `n: { "Name|Sex": [firstYear, ...counts] }`
  - `data/index.json` — top 5,000 names by peak count
  - `data/meta.json` — per-year aggregates and top-10 lists
  - `data/landing/{extinct,endangered,rising}.json`
- `scripts/build_pages.py` reads `data/index.json` and emits `name/<Name>/index.html` (Open Graph + JSON-LD + prerendered content) plus `sitemap.xml` and `robots.txt`.

**Runtime (vanilla JS, no framework):**

- `assets/app.js` exposes `window.NameVitals`:
  - `setupSearch()` — autocomplete against letter shards loaded on demand
  - `handleNameView()` — fetch shard, run `analyze()`, render report
  - `renderShareCard()` — Canvas → 1200×630 PNG download
- `assets/landing.js` exposes `window.renderLandingTable()` — sortable tables with inline SVG sparklines.
- Paths are resolved relative to `document.currentScript` so code works from both `/` and `/name/<Name>/`.

**Status thresholds (client-side `analyze()`):**

- Rising: last 5yr avg ≥ 1.2× previous 5yr avg
- Stable: within ±20%
- Declining: ≤ 0.8× (or latest count = 0)
- Endangered: peaked ≥ 200/yr, latest ≤ 10% of peak
- Extinct: zero in latest year AND no use in last 10 years
- "Zero" in SSA data means < 5 babies, not literally zero.

## Code Style

- **HTML:** hand-written; relative paths (`./assets/...` or `../../assets/...`).
- **CSS:** single `assets/style.css`, mobile-first, one breakpoint at `480px`, CSS custom properties for theming.
- **JavaScript:** vanilla ES6+, no semicolons, `const`/`let`, template strings for HTML generation. Stay dependency-free.
- **Python:** stdlib-first, `pathlib.Path` for all paths, scripts are directly runnable (`if __name__ == "__main__": main()`).

## Git Conventions

- `data_src/` is gitignored — never commit raw SSA files.
- `data/` and `name/` are **committed** — these are the build artifacts GitHub Pages serves.
- After regenerating data or pages, commit changes in `data/`, `name/`, `sitemap.xml`, and `robots.txt`.

## Deployment

Push to `main` → `.github/workflows/deploy.yml` fetches the latest `names.zip` from SSA.gov, runs both build scripts, and deploys to GitHub Pages automatically.
