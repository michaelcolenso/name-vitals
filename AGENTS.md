# Name Vitals — Agent Guide

A static, client-side web app that turns Social Security Administration baby-name records into a "vital-signs" report for any American name since 1880. Peak year, trajectory, all-time count, and a status verdict: rising, stable, declining, endangered, or extinct.

Everything is client-side against JSON data shards. No server, no tracking, no per-request build.

## Technology Stack

- **Frontend:** Plain HTML5, CSS3, vanilla JavaScript (ES6+). No frameworks, no bundlers, no npm.
- **Backend / Build:** Python 3 (stdlib only for the primary path; optional `rdata` package for a fallback source).
- **Hosting:** GitHub Pages (deployed as part of the `viz/` directory in the parent repo).
- **Canonical URL:** `https://michaelcolenso.github.io/name-vitals/`

## Project Layout

```
.
├── index.html                  Home + live search
├── extinct.html                Landing page: peaked ≥500, absent ≥10 yrs
├── endangered.html             Landing page: down ≥90% from peak
├── rising.html                 Landing page: latest decade ≥5× previous
├── about.html                  Methodology / data sources
├── name/<Name>/index.html      ~2,000 generated SEO pages for top names
├── sitemap.xml                 Generated URL list
├── robots.txt                  Generated allow + sitemap reference
├── assets/
│   ├── app.js                  Search, fetch, render, share card
│   ├── landing.js              Landing-page table + mini sparklines
│   └── style.css               Single stylesheet with CSS custom properties
├── data/
│   ├── index.json              Top-5,000 featured list + year totals
│   ├── meta.json               Per-year totals + top-10 by sex
│   ├── names/<A-Z>.json        Per-first-letter data shards
│   └── landing/*.json          Extinct / endangered / rising datasets
├── scripts/
│   ├── build_data.py           SSA source → JSON shards + landing sets
│   └── build_pages.py          Featured names → static HTML + sitemap
└── .github/workflows/deploy.yml  GitHub Actions workflow
```

## Build Commands

Rebuild data (run from the project root):

```bash
# Preferred: use raw SSA yob*.txt files
python3 scripts/build_data.py

# Then generate SEO pages and sitemap
python3 scripts/build_pages.py
```

If you need to refresh source data first:

```bash
curl -fsSL -o /tmp/names.zip https://www.ssa.gov/oact/babynames/names.zip
unzip -o /tmp/names.zip -d data_src
find data_src -type f ! -name 'yob*.txt' -delete

python3 scripts/build_data.py
python3 scripts/build_pages.py
```

Fallback path (using the committed `.rda` mirror) requires the `rdata` package:

```bash
python3 -m venv .venv && .venv/bin/pip install rdata
.venv/bin/python scripts/build_data.py
```

## Data Pipeline

`build_data.py` resolves its input source in this priority order:

1. `data_src/yob*.txt` — native SSA `Name,Sex,Count` files.
2. `$SSA_DATA_DIR/yob*.txt` — override via environment variable.
3. `../data/babynames.rda` — Hadley Wickham's CC0 mirror (1880–2017).

Outputs:
- `data/names/<A-Z>.json` — per-letter shards. Each shard contains `ym` (min year), `yM` (max year), and `n` (a map of `"Name|Sex"` to `[firstYear, countFirstYear, ..., countLastYearSeen]`).
- `data/index.json` — top 5,000 names by peak count, plus all-time totals by sex.
- `data/meta.json` — per-year totals, top-10 names per year, and row counts.
- `data/landing/*.json` — pre-computed lists for the three category landing pages.

`build_pages.py` consumes `data/index.json` and emits:
- `name/<Name>/index.html` for the top 2,000 featured names (SEO pages with Open Graph, JSON-LD, and prerendered `<noscript>` content).
- `sitemap.xml` and `robots.txt` at the project root.

## Runtime Architecture

The app is entirely static. JavaScript loads letter-shards on demand via `fetch()`:

- `assets/app.js` exposes `window.NameVitals` with these entry points:
  - `setupSearch(input, suggestions, submit, sexSelect)` — autocomplete against loaded shards.
  - `handleNameView(container, name, sexHint)` — fetch, analyze, and render a full report.
  - `renderShareCard(record)` — generate a 1200×630 PNG share card via `<canvas>`.
  - Utility helpers: `loadShard`, `loadIndex`, `analyze`, `buildSparkline`, `entryToSeries`, `titleCase`, `fmt`.
- `assets/landing.js` exposes `window.renderLandingTable(kind, targetElement)` — builds sortable-ish tables with inline SVG sparklines.

Paths are resolved relative to `document.currentScript` so the same code works from `/` and `/name/Emma/`.

## Status Definitions

The client-side `analyze()` function assigns a status based on the most recent decade of data:

- **Rising:** last 5-year average is ≥1.2× the previous 5-year average.
- **Stable:** last 5-year average is within ±20% of the previous 5-year average.
- **Declining:** last 5-year average is ≤0.8× the previous 5-year average (or latest count is zero).
- **Endangered:** peaked at ≥200 babies/year, but the latest year is ≤10% of that peak.
- **Extinct:** zero babies in the latest year and no recorded use in the last 10 years.

Note: a "zero" in SSA data means "fewer than five babies," not literally zero.

## Code Style Guidelines

- **HTML:** hand-written, no templating engine except the Python string template in `build_pages.py`. Use relative paths (`./assets/...` or `../../assets/...`).
- **CSS:** single file, mobile-first with one breakpoint at `480px`. Uses CSS custom properties for theming.
- **JavaScript:** vanilla ES6+, no semicolons in the existing style, `const`/`let` preferred, template strings for HTML generation. Keep it dependency-free.
- **Python:** standard-library-first. Type hints are used sparingly. Paths are built with `pathlib.Path`. Scripts are runnable directly (`if __name__ == "__main__": main()`).

## Testing

There is no automated test suite. Changes should be verified manually:

1. Run `python3 scripts/build_data.py` and confirm it prints row/year/name counts to stderr without errors.
2. Run `python3 scripts/build_pages.py` and confirm it prints the page/sitemap counts.
3. Open `index.html` in a browser, search a few names, and verify the report renders, sparklines draw, and share-card downloads work.
4. Open `extinct.html`, `endangered.html`, and `rising.html` and verify tables populate.
5. Check a generated `name/<Name>/index.html` page directly to ensure relative asset links resolve.

## Deployment

The site is deployed via `.github/workflows/deploy.yml`, which runs on every push to `main` or `master`. It:
- Sets up Python 3.11 on the runner.
- Downloads the latest `names.zip` from SSA.gov.
- Re-runs `build_data.py` and `build_pages.py`.
- Deploys the repo root to GitHub Pages.

## Security & Privacy Considerations

- No user data is collected or transmitted. All search and rendering happens client-side.
- The Amazon affiliate link in the report template uses `rel="nofollow sponsored"` and includes a blank `tag=` parameter (intended to be filled if an affiliate ID is ever added).
- No secrets, API keys, or environment-specific credentials are present in the built site.

## Git Conventions

- `data_src/` is gitignored (raw SSA source files should not be committed).
- `data/` and `name/` are **not** ignored — the committed build artifacts are what GitHub Pages serves.
- If you regenerate data or pages, commit the resulting changes in `data/`, `name/`, `sitemap.xml`, and `robots.txt`.
