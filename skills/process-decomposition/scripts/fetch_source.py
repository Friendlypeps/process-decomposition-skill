#!/usr/bin/env python3
"""
Fetch a source once, keep it on disk, and quote from it by character offset.

Reading a page through a browser tool gives you text you cannot cite: there is no
stable position to record, so every evidence span ends up with offset -1 and no
reader can check the quote. Fetching a full document into the conversation has
the opposite problem - it overflows the response and the run turns into document
wrangling. This does neither. The text lands in a file, and you pull the spans
you need.

    python scripts/fetch_source.py fetch URL --id S1 --out /tmp/src
    python scripts/fetch_source.py find "metaboric acid" --in /tmp/src/S1.txt
    python scripts/fetch_source.py window 4213 --in /tmp/src/S1.txt

`fetch` prints the `sources[]` entry to paste straight into the decomposition,
including `readable: false` when the fetch failed. Standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Some publishers refuse the default urllib agent outright.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
TIMEOUT_SECONDS = 45

DROP_BLOCKS = re.compile(r"<(script|style|noscript|svg|head)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
BREAKING = re.compile(r"</(p|div|li|tr|h[1-6]|section|article|br)\s*>|<br\s*/?>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
BLANK_RUN = re.compile(r"\n{3,}")
SPACE_RUN = re.compile(r"[ \t\r\f\v]+")


def to_text(raw: str) -> str:
    """
    HTML to plain text, keeping paragraph breaks so offsets fall in readable places.

    Deliberately not a parser: the sandbox is not guaranteed to have one, and a
    dependency that might be missing is worse than a regex that is merely blunt.
    """
    body = DROP_BLOCKS.sub(" ", raw)
    body = BREAKING.sub("\n", body)
    body = TAG.sub(" ", body)
    body = html.unescape(body)
    body = SPACE_RUN.sub(" ", body)
    body = "\n".join(line.strip() for line in body.split("\n"))
    return BLANK_RUN.sub("\n\n", body).strip()


def cmd_fetch(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.id}.txt"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    entry = {
        "source_id": args.id,
        "uri": args.url,
        "title": "",
        "kind": args.kind,
        "retrieved_at": now,
        "chars": 0,
        "readable": False,
    }

    request = urllib.request.Request(args.url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
        # A failed fetch is a result, not a crash: the caller records it as an
        # unreadable source and must not cite it.
        entry["note"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(entry, indent=2))
        return 1

    title = TITLE.search(raw)
    if title:
        entry["title"] = SPACE_RUN.sub(" ", html.unescape(title.group(1))).strip()[:200]

    text = to_text(raw)
    path.write_text(text, encoding="utf-8")
    entry.update({"chars": len(text), "readable": True, "path": str(path)})
    print(json.dumps(entry, indent=2))
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    """
    Register text obtained some other way, so it gets offsets like any fetch.

    Direct fetching fails for real reasons - a site that refuses datacenter
    egress, a page that needs JavaScript, a login wall. Text recovered through a
    browser or a search tool is still evidence; it just arrives without a
    position. Save it here and `find` works on it exactly as it would have.
    """
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.id}.txt"
    raw = sys.stdin.read() if args.text is None else args.text
    text = to_text(raw) if args.html else raw.strip()
    path.write_text(text, encoding="utf-8")
    print(json.dumps({
        "source_id": args.id,
        "uri": args.uri,
        "title": args.title,
        "kind": args.kind,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chars": len(text),
        "readable": True,
        "path": str(path),
        "note": f"retrieved via {args.via}",
    }, indent=2))
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    text = Path(args.source).read_text(encoding="utf-8")
    needle = args.phrase if args.regex else re.escape(args.phrase)
    flags = 0 if args.case_sensitive else re.IGNORECASE
    hits = []
    for match in re.finditer(needle, text, flags):
        start = max(0, match.start() - args.radius)
        end = min(len(text), match.end() + args.radius)
        hits.append({
            "offset": match.start(),
            "match": match.group(0),
            "context": SPACE_RUN.sub(" ", text[start:end].replace("\n", " ")).strip(),
        })
        if len(hits) >= args.limit:
            break
    print(json.dumps(hits, indent=2))
    return 0 if hits else 1


def cmd_window(args: argparse.Namespace) -> int:
    text = Path(args.source).read_text(encoding="utf-8")
    start = max(0, args.offset - args.radius)
    end = min(len(text), args.offset + args.radius)
    print(json.dumps({"offset": start, "text": text[start:end]}, indent=2))
    return 0


# The degree sign is optional: sources write "155 C" and "120~160 C" as often as
# "155 °C". Over-matching is fine here - this is a candidate list the caller
# confirms by reading the sentence around each hit.
QUANTITY_PATTERN = (
    r"\d[\d.,]*\s*(?:~|--|-|–|—|to)?\s*[\d.,]*\s*"
    r"(?:(?:°|º)?\s*(?:deg\.?\s*)?[CF]\b|\bK\b|\bbar\b|\bmbar\b|\bpsig?\b|\bkPa\b|\bMPa\b|"
    r"\batm\b|\btorr\b|\bmmHg\b|\bm3\b|\bL\b|\bkg/s\b|\bkg/h\b|\bt/h\b)"
)


def cmd_quantities(args: argparse.Namespace) -> int:
    """
    Every stated quantity with its offset. Which step it belongs to is a judgment.

    Always exits 0, including on an empty result: "the source states no
    conditions" is a finding this skill acts on, not a failure to report.
    """
    args.phrase, args.regex, args.case_sensitive = QUANTITY_PATTERN, True, False
    cmd_find(args)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download a URL and save its text")
    fetch.add_argument("url")
    fetch.add_argument("--id", required=True, help="source_id, e.g. S1 or P-6-S1")
    fetch.add_argument("--out", default="/tmp/src", help="directory for the saved text")
    fetch.add_argument("--kind", default="web", choices=["web", "pdf", "file", "figure", "patent"])
    fetch.set_defaults(func=cmd_fetch)

    save = sub.add_parser("save", help="register text fetched by other means (stdin, or --text)")
    save.add_argument("--id", required=True)
    save.add_argument("--uri", required=True)
    save.add_argument("--out", default="/tmp/src")
    save.add_argument("--title", default="")
    save.add_argument("--kind", default="web", choices=["web", "pdf", "file", "figure", "patent"])
    save.add_argument("--via", default="browser", help="how it was retrieved, recorded as a note")
    save.add_argument("--text", default=None, help="the text; omit to read stdin")
    save.add_argument("--html", action="store_true", help="strip tags before saving")
    save.set_defaults(func=cmd_save)

    find = sub.add_parser("find", help="locate a phrase and return its offset")
    find.add_argument("phrase")
    find.add_argument("--in", dest="source", required=True)
    find.add_argument("--radius", type=int, default=160)
    find.add_argument("--limit", type=int, default=20)
    find.add_argument("--regex", action="store_true")
    find.add_argument("--case-sensitive", action="store_true")
    find.set_defaults(func=cmd_find)

    window = sub.add_parser("window", help="read the text around an offset")
    window.add_argument("offset", type=int)
    window.add_argument("--in", dest="source", required=True)
    window.add_argument("--radius", type=int, default=400)
    window.set_defaults(func=cmd_window)

    quantities = sub.add_parser("quantities", help="every stated temperature, pressure, volume or flow")
    quantities.add_argument("--in", dest="source", required=True)
    quantities.add_argument("--radius", type=int, default=160)
    quantities.add_argument("--limit", type=int, default=60)
    quantities.set_defaults(func=cmd_quantities)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
