#!/usr/bin/env python3
"""Collect and analyse injury news from footactu.com (WordPress REST API).

Usage:
    python3 footactu/collect.py            # incremental update (only articles modified since last run)
    python3 footactu/collect.py --full     # full re-crawl of the whole archive

Outputs (under footactu/data/):
    articles.json   every collected article, keyed by WordPress id (append/update only)
    injuries.json   the subset classified as injury-related, with detected injury types
    report.md       analysis: totals, per competition/team category, injury types, trends, latest cases
    state.json      last run timestamp, used for incremental updates

Only the Python standard library is used. Requests are sequential with a delay
between them, and the site's robots.txt is respected (wp-json is not disallowed).
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

BASE = "https://footactu.com/wp-json/wp/v2"
USER_AGENT = "footactu-injury-collector/1.0 (+https://github.com/irrever/c-kdo-test)"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ARTICLES = os.path.join(DATA, "articles.json")
INJURIES = os.path.join(DATA, "injuries.json")
REPORT = os.path.join(DATA, "report.md")
STATE = os.path.join(DATA, "state.json")

# Injury signal: any of these (accent-insensitive, lowercase) marks an article as injury-related.
INJURY_SIGNALS = [
    r"blessure", r"blesse", r"forfait", r"indisponib", r"infirmerie", r"rupture",
    r"entorse", r"claquage", r"dechirure", r"pubalgie", r"tendon", r"ligament",
    r"ischio", r"sort sur blessure", r"absent", r"convalescence", r"soins",
    r"lesion", r"contusion", r"fracture", r"luxation", r"commotion",
]

# Injury types, to count what kind of problems are reported.
INJURY_TYPES = {
    "ischio-jambiers": r"\bischio",
    "ligaments croises (LCA)": r"\blca\b|ligaments? croises?",
    "ligament (autre)": r"\bligaments?\b",
    "tendon d'Achille": r"\bachille\b",
    "cuisse / claquage": r"\bcuisse|\bclaquage|\belongation",
    "mollet": r"\bmollet",
    "cheville / entorse": r"\bcheville|\bentorse",
    "genou": r"\bgenou",
    "hanche / aine / pubalgie": r"\bhanche|\baine\b|\bpubalgie",
    "dos / lombaires": r"\bdos\b|\blombaire",
    "epaule / bras": r"\bepaule|\bbras\b",
    "commotion": r"\bcommotion",
    "fracture": r"\bfracture",
    "crampes": r"\bcrampe",
    "maladie / virus": r"\bmalade|\bvirus\b|\bgrippe\b|\bcovid",
}

MONTHS_FR = ["janv", "fevr", "mars", "avr", "mai", "juin", "juil", "aout", "sept", "oct", "nov", "dec"]


def norm(text: str) -> str:
    """Lowercase and strip accents so keyword matching is accent-insensitive."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def strip_html(raw: str) -> str:
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def http_json(url: str, retries: int = 4):
    """GET a JSON endpoint with backoff on rate limiting and transient errors.

    Returns (data, headers). Raises on final failure.
    """
    delay = 2.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8")), resp.headers
        except urllib.error.HTTPError as e:
            if e.code == 400 and "rest_post_invalid_page_number" in e.read().decode("utf-8", "ignore"):
                return [], {}
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"gave up on {url}")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    # Compact, key-sorted output keeps diffs small when the file is committed.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, path)


def fetch_categories(delay: float) -> dict:
    cats = {}
    page = 1
    while True:
        data, headers = http_json(f"{BASE}/categories?per_page=100&page={page}&_fields=id,name,slug,parent")
        if not data:
            break
        for c in data:
            cats[c["id"]] = {"name": html.unescape(c["name"]), "slug": c["slug"], "parent": c.get("parent", 0)}
        total_pages = int(headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(delay)
    return cats


def fetch_posts(modified_after: str | None, delay: float):
    """Yield every post (optionally only those modified after a timestamp)."""
    page = 1
    fields = "id,date,modified,link,title,excerpt,content,categories"
    while True:
        params = {"per_page": 100, "page": page, "orderby": "modified", "order": "desc", "_fields": fields}
        if modified_after:
            params["modified_after"] = modified_after
        url = f"{BASE}/posts?{urllib.parse.urlencode(params)}"
        data, headers = http_json(url)
        if not data:
            break
        for p in data:
            yield p
        total_pages = int(headers.get("X-WP-TotalPages", 1))
        print(f"  page {page}/{total_pages} ({len(data)} posts)", file=sys.stderr)
        if page >= total_pages:
            break
        page += 1
        time.sleep(delay)


def classify(article: dict) -> dict | None:
    """Return injury info for an article, or None if it is not injury-related."""
    head = norm(f"{article['title']} {article['excerpt']}")
    text = norm(f"{article['title']} {article['excerpt']} {article['content']}")
    signals = [s for s in INJURY_SIGNALS if re.search(s, text)]
    # Strong injury wording. "rupture" and "forfait" alone are too ambiguous (contracts, prices), so they only count
    # next to a match context or an explicit ligament/tendon rupture.
    strong = (r"\bblessure|\bblesse|\bindisponib|\binfirmerie|\bentorse|\bclaquage|\bpubalgie|"
              r"\bforfait\b.{0,60}\b(match|rencontre|sélection|selection|coupe|bleus|contre|face)|"
              r"\brupture (du|des|d'un|de) (ligament|tendon)")
    # Accept when the wording is in the headline or standfirst, or repeated in the body (article about an injury).
    in_head = re.search(strong, head)
    body_hits = len(re.findall(strong, text))
    if not in_head and body_hits < 2:
        return None
    types = [name for name, pat in INJURY_TYPES.items() if re.search(pat, text)]
    return {"signals": signals, "injury_types": types}


def build_entry(post: dict, cats: dict) -> dict:
    title = strip_html(post["title"]["rendered"])
    excerpt = strip_html(post.get("excerpt", {}).get("rendered", ""))
    content = strip_html(post.get("content", {}).get("rendered", ""))[:6000]
    names = [cats[c]["name"] for c in post.get("categories", []) if c in cats]
    entry = {
        "id": post["id"],
        "date": post["date"],
        "modified": post["modified"],
        "link": post["link"],
        "title": title,
        "excerpt": excerpt[:600],
        "content": content,
        "categories": names,
    }
    # Classify now, while the full text is available; the body is dropped later for non-injury articles.
    entry["injury"] = classify(entry)
    return entry


def analyse(articles: dict) -> dict:
    injuries = {}
    for aid, a in articles.items():
        info = a.get("injury")
        if info is None and "injury" not in a:
            info = classify(a)  # legacy entries without a stored classification
        if info:
            injuries[aid] = {**{k: a[k] for k in ("id", "date", "title", "link", "categories")}, **info}
    month_counts = Counter(v["date"][:7] for v in injuries.values())
    type_counts = Counter(t for v in injuries.values() for t in v["injury_types"])
    cat_counts = Counter(c for v in injuries.values() for c in v["categories"])
    return {"injuries": injuries, "by_month": month_counts, "by_type": type_counts, "by_category": cat_counts,
            "total_articles": len(articles)}


def write_report(stats: dict, run_at: str) -> None:
    lines = [f"# Blessures footactu : analyse automatique", "", f"Dernière mise à jour : {run_at} (UTC)", ""]
    lines += [f"- Articles collectés : **{stats['total_articles']}**",
              f"- Articles liés à une blessure : **{len(stats['injuries'])}**", ""]

    lines += ["## Volume par mois", "", "| Mois | Articles blessures |", "|---|---|"]
    for m, n in sorted(stats["by_month"].items()):
        lines.append(f"| {m} | {n} |")
    lines.append("")

    lines += ["## Types de blessure mentionnés", "", "| Type | Occurrences |", "|---|---|"]
    for t, n in stats["by_type"].most_common():
        lines.append(f"| {t} | {n} |")
    lines.append("")

    lines += ["## Rubriques les plus concernées (compétitions et équipes)", "", "| Rubrique | Articles |", "|---|---|"]
    for c, n in stats["by_category"].most_common(40):
        lines.append(f"| {c} | {n} |")
    lines.append("")

    lines += ["## 40 cas les plus récents", ""]
    recent = sorted(stats["injuries"].values(), key=lambda v: v["date"], reverse=True)[:40]
    for v in recent:
        types = ", ".join(v["injury_types"]) or "type non précisé"
        cats = ", ".join(v["categories"][:3])
        lines.append(f"- {v['date'][:10]} · [{v['title']}]({v['link']}) · {cats} · {types}")
    lines.append("")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="re-crawl the whole archive")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    state = load_json(STATE, {})
    articles = load_json(ARTICLES, {})  # keys are str(id)
    modified_after = None if args.full else state.get("last_modified_seen")

    run_started = dt.datetime.now(dt.timezone.utc)
    print(f"Mode: {'full' if modified_after is None else 'incremental since ' + modified_after}", file=sys.stderr)

    cats = fetch_categories(args.delay)
    newest = modified_after
    updated = 0
    for post in fetch_posts(modified_after, args.delay):
        entry = build_entry(post, cats)
        articles[str(entry["id"])] = entry
        updated += 1
        if newest is None or entry["modified"] > newest:
            newest = entry["modified"]

    stats = analyse(articles)
    # Keep full text only for injury-related articles; the rest keep their title and excerpt. This keeps the
    # committed archive small. A changed article is re-fetched in full on the next incremental run.
    for aid, a in articles.items():
        if aid not in stats["injuries"]:
            a.pop("content", None)
    save_json(ARTICLES, articles)
    save_json(INJURIES, stats["injuries"])
    write_report(stats, run_started.strftime("%Y-%m-%d %H:%M"))
    save_json(STATE, {
        "last_run": run_started.isoformat(),
        "last_modified_seen": newest,
        "articles_total": len(articles),
        "injury_articles": len(stats["injuries"]),
    })
    print(f"Updated {updated} posts; total {len(articles)} articles, {len(stats['injuries'])} injury-related.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
