#!/usr/bin/env python3
"""Upwork Job Radar - fetch marketplace job postings via the official GraphQL API.

Runs hourly via GitHub Actions between 01:00 and 06:00 Europe/Berlin.
The script itself checks the Berlin hour, so daylight saving time is handled.

Required environment variables:
  UPWORK_CLIENT_ID
  UPWORK_CLIENT_SECRET
  UPWORK_REFRESH_TOKEN

Set RADAR_FORCE=1 to skip the time-window check (manual test runs).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except ImportError:
    BERLIN = timezone(timedelta(hours=1), "Berlin")

TOKEN_URL = "https://www.upwork.com/ab/account-security/oauth2/token"
GRAPHQL_URL = "https://www.upwork.com/graphql"
PAGE_SIZE = 50
MAX_PAGES = 2
REQUEST_PAUSE_S = 2.5
RETENTION_DAYS = 14

QUERY = """
query marketplaceJobPostingsSearch(
  $marketPlaceJobFilter: MarketplaceJobPostingsSearchFilter,
  $searchType: MarketplaceJobPostingSearchType,
  $sortAttributes: [MarketplaceJobPostingSearchSortAttribute]
) {
  marketplaceJobPostingsSearch(
    marketPlaceJobFilter: $marketPlaceJobFilter,
    searchType: $searchType,
    sortAttributes: $sortAttributes
  ) {
    totalCount
    edges { node { id title description createdDateTime ciphertext } }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def log(msg):
    print(msg, flush=True)


def berlin_now():
    return datetime.now(BERLIN)


def in_night_window(now):
    return now.hour in (1, 2, 3, 4, 5, 6)


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_access_token():
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": os.environ["UPWORK_CLIENT_ID"],
        "client_secret": os.environ["UPWORK_CLIENT_SECRET"],
        "refresh_token": os.environ["UPWORK_REFRESH_TOKEN"],
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    return payload["access_token"]


def graphql(token, variables):
    body = json.dumps({"query": QUERY, "variables": variables}).encode("utf-8")
    last_error = None
    for attempt in range(3):
        req = urllib.request.Request(GRAPHQL_URL, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 30 * (attempt + 1)
                log("  rate limited (HTTP 429), waiting %ss" % wait)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("GraphQL request failed after retries: %s" % last_error)


def build_filter(term, after):
    expr = term.get("expression", "").strip()
    field = term.get("field", "searchTerm")
    filt = {"pagination_eq": {"first": PAGE_SIZE, "after": after}}
    if field == "titleExpression":
        filt["titleExpression_eq"] = expr
    elif field == "skillExpression":
        filt["skillExpression_eq"] = expr
    else:
        filt["searchTerm_eq"] = {"andTerms_all": [expr]}
    return filt


def fetch_term(token, term):
    jobs = []
    after = "0"
    for _page in range(MAX_PAGES):
        variables = {
            "marketPlaceJobFilter": build_filter(term, after),
            "searchType": "USER_JOBS_SEARCH",
            "sortAttributes": [{"field": "RECENCY"}],
        }
        result = graphql(token, variables)
        if result.get("errors"):
            for err in result["errors"]:
                log("  GraphQL error: %s" % err.get("message"))
            break
        conn = (result.get("data") or {}).get("marketplaceJobPostingsSearch") or {}
        for edge in conn.get("edges") or []:
            node = edge.get("node") or {}
            if node.get("id"):
                jobs.append(node)
        info = conn.get("pageInfo") or {}
        if not info.get("hasNextPage") or not info.get("endCursor"):
            break
        after = info["endCursor"]
        time.sleep(REQUEST_PAUSE_S)
    return jobs


def job_url(node):
    ct = node.get("ciphertext")
    return ("https://www.upwork.com/o/jobs/job/~%s/" % ct) if ct else None


def main():
    force = os.environ.get("RADAR_FORCE") == "1"
    now = berlin_now()
    if not force and not in_night_window(now):
        log("Outside 01:00-06:00 Berlin window (%s), skipping."
            % now.strftime("%H:%M"))
        return 0

    config = read_json("config/search_terms.json", {})
    terms = (config or {}).get("terms") or []
    if not terms:
        log("No search terms configured in config/search_terms.json")
        return 0

    token = get_access_token()
    log("Access token acquired. Fetching %d terms." % len(terms))

    seen = read_json("state/seen.json", {})
    cutoff = (now - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    seen = {jid: ts for jid, ts in seen.items()
            if isinstance(ts, str) and ts[:10] >= cutoff}

    today = now.strftime("%Y-%m-%d")
    day_path = os.path.join("data", today + ".json")
    day_data = read_json(day_path, {"date": today, "jobs": []})

    new_count = 0
    for term in terms:
        label = term.get("label") or term.get("expression")
        log("Fetching term: %s" % label)
        try:
            jobs = fetch_term(token, term)
        except Exception as e:
            log("  ERROR for '%s': %s" % (label, e))
            continue
        for node in jobs:
            jid = node["id"]
            if jid in seen:
                continue
            seen[jid] = now.isoformat()
            new_count += 1
            day_data["jobs"].append({
                "id": jid,
                "title": node.get("title"),
                "url": job_url(node),
                "description": node.get("description"),
                "createdDateTime": node.get("createdDateTime"),
                "term": label,
                "first_seen": now.isoformat(),
            })
            log("  new: %s" % (node.get("title") or jid))
        time.sleep(REQUEST_PAUSE_S)

    write_json(day_path, day_data)
    write_json("state/seen.json", seen)
    write_json("data/last_run.json", {
        "run_at": now.isoformat(),
        "terms": len(terms),
        "new_jobs": new_count,
        "day_file": day_path,
        "total_today": len(day_data["jobs"]),
    })
    log("Run done: %d new jobs, %d total today."
        % (new_count, len(day_data["jobs"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
