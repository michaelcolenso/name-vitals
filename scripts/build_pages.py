"""
Generate per-name SEO pages + sitemap + robots.txt for Name Vitals.

For each featured name (top N by peak count, across both sexes), emit:
  name-vitals/name/<Name>/index.html

Each page is pre-filled with name-specific <title>, <meta description>,
Open Graph tags, and a minimal prerendered pitch so crawlers & social unfurls
see real content. The client-side JS still renders the full interactive report.

Also emits name-vitals/sitemap.xml and name-vitals/robots.txt.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT
INDEX = OUT / "data" / "index.json"
TOP_N = 2000
SITE_ORIGIN = "https://michaelcolenso.github.io"
SITE_BASE = "/name-vitals"
# Standalone repo: build_pages.py lives at scripts/, parents[1] is repo root.


PAGE_TMPL = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{name} name popularity, meaning & history | Name Vitals</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:title" content="{name} · Name Vitals">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="profile">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&display=swap">
  <link rel="stylesheet" href="../../assets/style.css">
  <script type="application/ld+json">
{jsonld}
  </script>
</head>
<body>
  <div class="page">
    <header class="site">
      <a class="brand" href="../../">Name Vitals</a>
      <nav>
        <a href="../../extinct.html">Extinct</a>
        <a href="../../endangered.html">Endangered</a>
        <a href="../../rising.html">Rising</a>
        <a href="../../about.html">About</a>
      </nav>
    </header>
    <noscript>
      <h1>{name}</h1>
      <p class="lede">{description}</p>
      <p>Interactive sparkline and share card require JavaScript.</p>
    </noscript>
    <div id="view-name"></div>
    <footer class="site">
      <div>Based on SSA records.</div>
      <div><a href="../../about.html">About</a></div>
    </footer>
  </div>
  <script src="../../assets/app.js"></script>
  <script>
    NameVitals.handleNameView(document.getElementById("view-name"), {name_js}, {sex_js});
  </script>
</body>
</html>
"""


def slug(name: str) -> str:
    return name  # names are already ASCII letters / apostrophes; leave as-is


def page_for(name: str, sex_mask: int, peak_count: int, peak_year: int) -> tuple[str, str]:
    sex = None
    if sex_mask == 1:
        sex = "M"
    elif sex_mask == 2:
        sex = "F"
    sex_label = {"M": "boys", "F": "girls", None: "babies"}[sex]
    description = (
        f"{name} peaked for American {sex_label} in {peak_year} "
        f"with {peak_count:,} babies. See its full 138-year trajectory and share card."
    )
    canonical = f"{SITE_ORIGIN}{SITE_BASE}/name/{slug(name)}/"
    jsonld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "name": f"{name} name history",
            "headline": f"{name} name history & popularity",
            "description": description,
            "url": canonical,
            "about": {"@type": "Thing", "name": name, "additionalType": "GivenName"},
            "isBasedOn": {"@type": "Dataset", "url": "https://www.ssa.gov/oact/babynames/"},
            "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        },
        separators=(",", ":"),
    )
    html = PAGE_TMPL.format(
        name=name,
        description=description,
        canonical=canonical,
        jsonld=jsonld,
        name_js=json.dumps(name),
        sex_js=json.dumps(sex),
    )
    return name, html


def main() -> None:
    if not INDEX.exists():
        sys.exit(f"missing {INDEX}; run build_data.py first")
    data = json.loads(INDEX.read_text())
    featured = data["featured"][:TOP_N]
    names_root = OUT / "name"
    names_root.mkdir(exist_ok=True)

    urls = [f"{SITE_ORIGIN}{SITE_BASE}/"]
    for page in ("extinct.html", "endangered.html", "rising.html", "about.html"):
        urls.append(f"{SITE_ORIGIN}{SITE_BASE}/{page}")

    count = 0
    for row in featured:
        name, sex_mask, peak_count, peak_year = row
        if not name or not name[0].isalpha():
            continue
        _, html = page_for(name, sex_mask, peak_count, peak_year)
        d = names_root / name
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(html)
        urls.append(f"{SITE_ORIGIN}{SITE_BASE}/name/{name}/")
        count += 1

    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[f"  <url><loc>{u}</loc></url>" for u in urls],
            "</urlset>",
        ]
    )
    (OUT / "sitemap.xml").write_text(sitemap)
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_ORIGIN}{SITE_BASE}/sitemap.xml\n"
    )

    print(f"wrote {count} name pages + sitemap with {len(urls)} urls", file=sys.stderr)


if __name__ == "__main__":
    main()
