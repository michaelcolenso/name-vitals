"""
Build client-side data for Name Vitals.

INPUTS (first match wins):
  1. data_src/yob*.txt    — native SSA files (Name,Sex,Count)
  2. $SSA_DATA_DIR/yob*.txt — override for CI checkouts
  3. data/babynames.rda     — Hadley Wickham's CC0 mirror (1880-2017)

OUTPUTS (written to data/):
  names/<letter>.json       Per-first-letter shard. See SHARD FORMAT below.
  index.json                Top names for featured/autocomplete fallback.
  meta.json                 Totals per year by sex + top-10 per year + year range.
  landing/extinct.json      Peaked >=500, absent from last 10 years.
  landing/endangered.json   Declined >=90% from peak, <=50 last year, peaked >=500.
  landing/rising.json       Latest decade >=5x previous decade, latest year >=100.

SHARD FORMAT:
  { "ym": 1880, "yM": 2024, "n": {
      "Amy|F": [firstYear, countFirstYear, countFirstYear+1, ..., countLastYearSeen],
      "Amy|M": [...],
      ...
  }}
  The count array runs contiguously from firstYear to the last year the
  name appeared (>=5 per SSA rules). Years outside that window are zero.

Re-run after refreshing the source; the schema is stable.
"""
from __future__ import annotations
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterator

HERE = Path(__file__).resolve()
SITE = HERE.parents[1]            # repo root
REPO = HERE.parents[3]            # repo root
OUT = SITE / "data"
NAMES_DIR = OUT / "names"
LANDING_DIR = OUT / "landing"

# Candidate input sources, in priority order.
LOCAL_YOB_DIR = SITE / "data_src"
ENV_YOB_DIR = Path(os.environ["SSA_DATA_DIR"]) if os.environ.get("SSA_DATA_DIR") else None
RDA_SRC = REPO / "data" / "babynames.rda"

YOB_RE = re.compile(r"^yob(\d{4})\.txt$", re.IGNORECASE)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(obj, f, separators=(",", ":"))


def shard_letter(name: str) -> str:
    ch = name[:1].upper()
    return ch if "A" <= ch <= "Z" else "_"


def iter_yob_rows(folder: Path) -> Iterator[tuple[int, str, str, int]]:
    files = sorted(p for p in folder.iterdir() if YOB_RE.match(p.name))
    if not files:
        raise FileNotFoundError(f"no yob*.txt files in {folder}")
    for p in files:
        year = int(YOB_RE.match(p.name).group(1))
        with p.open(newline="") as f:
            for row in csv.reader(f):
                # SSA files: Name,Sex,Count — no header.
                if len(row) != 3:
                    continue
                name, sex, n = row[0].strip(), row[1].strip(), row[2].strip()
                if not name or not sex or not n:
                    continue
                yield year, sex, name, int(n)


def iter_rda_rows() -> Iterator[tuple[int, str, str, int]]:
    try:
        import rdata  # type: ignore
    except ImportError:
        sys.exit(
            "No yob*.txt files found and `rdata` isn't installed for the .rda fallback. "
            f"Either drop yob*.txt into {LOCAL_YOB_DIR}/ (or set SSA_DATA_DIR), "
            "or run: pip install rdata"
        )
    if not RDA_SRC.exists():
        sys.exit(f"missing {RDA_SRC}; no input found")
    parsed = rdata.read_rda(str(RDA_SRC))
    df = parsed["babynames"]
    for year, sex, name, n in zip(df["year"], df["sex"], df["name"], df["n"], strict=True):
        yield int(year), str(sex), str(name), int(n)


def resolve_source() -> tuple[str, Iterator[tuple[int, str, str, int]]]:
    for candidate in (LOCAL_YOB_DIR, ENV_YOB_DIR):
        if candidate and candidate.exists() and any(YOB_RE.match(p.name) for p in candidate.iterdir()):
            return f"yob*.txt in {candidate}", iter_yob_rows(candidate)
    return f"rda mirror {RDA_SRC}", iter_rda_rows()


def main() -> None:
    NAMES_DIR.mkdir(parents=True, exist_ok=True)
    LANDING_DIR.mkdir(parents=True, exist_ok=True)

    label, row_iter = resolve_source()
    print(f"loading: {label}", file=sys.stderr)

    # series[name][sex][year] = count
    series: dict[str, dict[str, dict[int, int]]] = defaultdict(lambda: defaultdict(dict))
    totals_by_year: dict[int, dict[str, int]] = defaultdict(lambda: {"M": 0, "F": 0})
    rows_by_year: dict[int, list[tuple[int, str, str]]] = defaultdict(list)

    total_rows = 0
    ym, yM = 9999, 0
    for y, sex, name, c in row_iter:
        total_rows += 1
        if y < ym: ym = y
        if y > yM: yM = y
        series[name][sex][y] = c
        totals_by_year[y][sex] += c
        rows_by_year[y].append((c, name, sex))

    print(f"rows={total_rows:,}  years={ym}-{yM}  names={len(series):,}", file=sys.stderr)

    # Per-letter shards
    shards: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for name, by_sex in series.items():
        letter = shard_letter(name)
        for sex, yr_counts in by_sex.items():
            if not yr_counts:
                continue
            first = min(yr_counts)
            last = max(yr_counts)
            arr = [first] + [yr_counts.get(y, 0) for y in range(first, last + 1)]
            shards[letter][f"{name}|{sex}"] = arr

    for letter, rows in shards.items():
        write_json(NAMES_DIR / f"{letter}.json", {"ym": ym, "yM": yM, "n": rows})

    # Autocomplete featured list (top 5000 by peak)
    index_rows: list[list] = []
    for name, by_sex in series.items():
        mask = 0
        peak_count = 0
        peak_year = 0
        for sex, yr_counts in by_sex.items():
            mask |= 1 if sex == "M" else 2
            for y, c in yr_counts.items():
                if c > peak_count:
                    peak_count = c
                    peak_year = y
        index_rows.append([name, mask, peak_count, peak_year])
    index_rows.sort(key=lambda r: (-r[2], r[0]))
    featured = index_rows[:5000]

    totals_M = [totals_by_year[y]["M"] for y in range(ym, yM + 1)]
    totals_F = [totals_by_year[y]["F"] for y in range(ym, yM + 1)]

    write_json(
        OUT / "index.json",
        {
            "ym": ym,
            "yM": yM,
            "totals": {"M": totals_M, "F": totals_F},
            "featured": featured,
            "totalNames": len(index_rows),
        },
    )

    top_per_year = {}
    for y, rows in rows_by_year.items():
        ms = sorted([r for r in rows if r[2] == "M"], key=lambda t: -t[0])[:10]
        fs = sorted([r for r in rows if r[2] == "F"], key=lambda t: -t[0])[:10]
        top_per_year[str(y)] = [[n, s, c] for c, n, s in (fs + ms)]
    write_json(
        OUT / "meta.json",
        {
            "ym": ym,
            "yM": yM,
            "totalNames": len(series),
            "totalRows": total_rows,
            "totalsByYear": {str(y): totals_by_year[y] for y in range(ym, yM + 1)},
            "top10PerYear": top_per_year,
        },
    )

    # Landing-page datasets
    last_year = yM
    first_year = ym

    def decade_total(name, sex, start):
        return sum(c for y, c in series[name][sex].items() if start <= y < start + 10)

    extinct: list[dict] = []
    endangered: list[dict] = []
    rising: list[dict] = []

    for name, by_sex in series.items():
        for sex, yr_counts in by_sex.items():
            if not yr_counts:
                continue
            peak_y = max(yr_counts, key=lambda y: yr_counts[y])
            peak_c = yr_counts[peak_y]
            latest = yr_counts.get(last_year, 0)
            last_seen = max(yr_counts)
            # Full-range series so extinct/endangered sparklines show the
            # dramatic long zero-tail that makes the page click.
            series_arr = [yr_counts.get(y, 0) for y in range(first_year, last_year + 1)]

            if peak_c >= 500 and latest == 0 and last_year - last_seen >= 10:
                extinct.append({
                    "name": name, "sex": sex,
                    "peakYear": peak_y, "peakCount": peak_c,
                    "lastYearSeen": last_seen, "series": series_arr,
                })
            if peak_c >= 500 and 0 < latest <= 50 and latest <= peak_c * 0.1:
                endangered.append({
                    "name": name, "sex": sex,
                    "peakYear": peak_y, "peakCount": peak_c,
                    "latestCount": latest,
                    "declinePct": round(100 * (1 - latest / peak_c), 1),
                    "series": series_arr,
                })
            prev = decade_total(name, sex, last_year - 19)
            curr = decade_total(name, sex, last_year - 9)
            if latest >= 100 and prev >= 10 and curr >= prev * 5:
                rising.append({
                    "name": name, "sex": sex,
                    "latestCount": latest,
                    "prevDecadeTotal": prev, "currDecadeTotal": curr,
                    "growthX": round(curr / prev, 1) if prev else None,
                    "series": series_arr,
                })

    extinct.sort(key=lambda r: -r["peakCount"])
    endangered.sort(key=lambda r: -r["peakCount"])
    rising.sort(key=lambda r: -r["currDecadeTotal"])

    write_json(LANDING_DIR / "extinct.json", {"yM": last_year, "rows": extinct[:500]})
    write_json(LANDING_DIR / "endangered.json", {"yM": last_year, "rows": endangered[:500]})
    write_json(LANDING_DIR / "rising.json", {"yM": last_year, "rows": rising[:500]})

    print(f"extinct={len(extinct)}  endangered={len(endangered)}  rising={len(rising)}", file=sys.stderr)
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
