#!/usr/bin/env python3
"""
Job Search Scanner - Monitor career pages for new postings matching your criteria.

Loads search configuration from job_search_config.json, fetches career pages,
extracts job listings, and reports new postings not yet tracked.

Usage:
    python3 scan_jobs.py                # Scan career pages, report new postings
    python3 scan_jobs.py --show-queries # Also print saved search queries to re-run
    python3 scan_jobs.py --verbose      # Show all checked URLs, not just new ones
    python3 scan_jobs.py --update-seen  # Mark all current postings as "seen"
"""

import argparse
import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'job_search_config.json'
TRACKER_FILE = Path(__file__).parent / 'job_tracker.csv'

# ── URL extraction patterns per platform ──────────────────────────────────────

# Each pattern extracts (url, title) pairs directly from page HTML.
PLATFORM_EXTRACTORS = {
    # Greenhouse: <a href="...jobs/ID..."><p class="body body--medium">Title</p>...</a>
    'greenhouse': re.compile(
        r'<a[^>]*href="(https?://(?:job-boards\.)?greenhouse\.io/[^/]+/jobs/\d+[^"]*)"[^>]*>'
        r'.*?<p[^>]*class="[^"]*body--medium[^"]*"[^>]*>\s*([^<]+?)\s*(?:<[^/]|</p>)',
        re.IGNORECASE | re.DOTALL,
    ),
    # Lever: <a class="posting-title" href="..."><h5 data-qa="posting-name">Title</h5>...</a>
    'lever': re.compile(
        r'<a[^>]*class="posting-title"[^>]*href="(https?://jobs\.lever\.co/[^/]+/[0-9a-f-]+)"[^>]*>'
        r'\s*<h5[^>]*>\s*([^<]+?)\s*</h5>',
        re.IGNORECASE | re.DOTALL,
    ),
    # Dover: extract from page data
    'dover': re.compile(
        r'href="(https?://app\.dover\.com/apply/[^/]+/[0-9a-f-]+[^"]*)"[^>]*>'
        r'\s*([^<]+?)\s*</a>',
        re.IGNORECASE | re.DOTALL,
    ),
    # Workable
    'workable': re.compile(
        r'href="(https?://apply\.workable\.com/[^/]+/j/[A-Za-z0-9]+/?)"[^>]*>'
        r'[^<]*?([^<]+?)\s*</a>',
        re.IGNORECASE | re.DOTALL,
    ),
    # Workday
    'workday': re.compile(
        r'href="(https?://[^"]*\.myworkdayjobs\.com/[^"]*?/job/[^"]+)"[^>]*>'
        r'\s*([^<]+?)\s*</a>',
        re.IGNORECASE | re.DOTALL,
    ),
}

# Generic fallback: extract any absolute link that looks like a job posting
GENERIC_JOB_LINK = re.compile(
    r'href="(https?://[^"]*(?:/jobs?/|/careers?/|/positions?/|/openings?/|/apply/)[^"]*)"',
    re.IGNORECASE,
)


# ── Fetch helper (reused from check_job_urls.py) ─────────────────────────────

def fetch_url(url, timeout=20):
    """Fetch a URL with curl and return (http_code, body)."""
    try:
        result = subprocess.run(
            [
                'curl', '-sL',
                '--max-time', str(timeout),
                '--max-redirs', '5',
                '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                '-w', '\n__HTTP_CODE__:%{http_code}',
                url,
            ],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        output = result.stdout
        code_match = re.search(r'__HTTP_CODE__:(\d+)', output)
        http_code = int(code_match.group(1)) if code_match else 0
        body = output[:output.rfind('__HTTP_CODE__:')] if code_match else output
        return http_code, body
    except (subprocess.TimeoutExpired, Exception) as e:
        return 0, str(e)


# ── Job extraction ────────────────────────────────────────────────────────────

def extract_jobs_from_page(html, platform, page_url):
    """Extract (url, title) pairs from a career page's HTML."""
    jobs = []

    extractor = PLATFORM_EXTRACTORS.get(platform)
    if extractor:
        for match in extractor.finditer(html):
            url, title = match.group(1), match.group(2).strip()
            # Clean HTML entities
            title = title.replace('&amp;', '&').replace('&#x27;', "'")
            jobs.append((url.rstrip('/'), title or _title_from_url(url)))
    else:
        # Generic: extract any job-like links from the page
        links = GENERIC_JOB_LINK.findall(html)
        # Also try extracting links from JSON-LD or data attributes
        json_links = re.findall(
            r'"(?:url|href|apply_url)"\s*:\s*"(https?://[^"]*(?:/jobs?/|/careers?/|/positions?/)[^"]*)"',
            html, re.IGNORECASE,
        )
        links = list(set(links + json_links))
        for link in links:
            # Skip assets, stylesheets, images
            if re.search(r'\.(css|js|png|jpg|svg|ico|woff)', link, re.IGNORECASE):
                continue
            title = _title_from_url(link)
            jobs.append((link.rstrip('/'), title))

    # Deduplicate by URL
    seen = set()
    unique = []
    for url, title in jobs:
        normalized = re.sub(r'[?#].*', '', url).rstrip('/')
        if normalized not in seen:
            seen.add(normalized)
            unique.append((url, title))

    return unique


def _title_from_url(url):
    """Derive a rough title from a URL path."""
    path = url.rstrip('/').rsplit('/', 1)[-1]
    path = re.sub(r'[0-9a-f-]{20,}', '', path)  # strip UUIDs / IDs
    path = re.sub(r'^\d+[-_]?', '', path)  # strip leading numeric IDs
    path = path.replace('-', ' ').replace('_', ' ').strip()
    return path.title() if path else '(untitled)'


def matches_keywords(title, keywords):
    """Return True if the title matches at least one keyword (case-insensitive).
    If keywords list is empty, all jobs match."""
    if not keywords:
        return True
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


# ── Tracker integration ──────────────────────────────────────────────────────

def load_tracked_urls():
    """Load all Job URLs from the tracker CSV."""
    urls = set()
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, newline='') as f:
            for row in csv.DictReader(f):
                url = row.get('Job URL', '').strip()
                if url:
                    urls.add(re.sub(r'[?#].*', '', url).rstrip('/'))
    return urls


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_config():
    """Load and return the search config dict."""
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config):
    """Write the config back to disk (preserving formatting)."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
        f.write('\n')


# ── Scanning logic ────────────────────────────────────────────────────────────

def scan_career_page(page):
    """Fetch one career page and return extracted jobs."""
    company = page['company']
    url = page['url']
    platform = page.get('platform', 'generic')
    keywords = page.get('keywords', [])

    http_code, body = fetch_url(url)
    if http_code == 0:
        return company, url, [], f'Connection failed'
    if http_code >= 400:
        return company, url, [], f'HTTP {http_code}'

    all_jobs = extract_jobs_from_page(body, platform, url)
    matched = [(u, t) for u, t in all_jobs if matches_keywords(t, keywords)]

    return company, url, matched, None


def run_scan(config, verbose=False, update_seen=False):
    """Scan all career pages and report results."""
    pages = config.get('career_pages', [])
    checked_urls = config.get('checked_urls', {})
    tracked_urls = load_tracked_urls()
    today = datetime.now().strftime('%Y-%m-%d')

    if not pages:
        print('No career pages configured.')
        return

    print(f'Scanning {len(pages)} career pages...\n')

    # Fetch all pages in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(scan_career_page, page): page
            for page in pages
        }
        for future in as_completed(futures):
            page = futures[future]
            company, url, jobs, error = future.result()
            results[page['company']] = (url, jobs, error)

    # Classify and report
    new_total = 0
    seen_total = 0
    error_pages = []

    for page in pages:
        company = page['company']
        url, jobs, error = results[company]

        if error:
            error_pages.append((company, error))
            if verbose:
                print(f'  ERROR   {company}: {error}')
            continue

        new_jobs = []
        seen_jobs = []
        for job_url, title in jobs:
            normalized = re.sub(r'[?#].*', '', job_url).rstrip('/')
            already_known = (
                normalized in checked_urls
                or normalized in tracked_urls
            )
            if already_known:
                seen_jobs.append((job_url, title))
            else:
                new_jobs.append((job_url, title))

        new_total += len(new_jobs)
        seen_total += len(seen_jobs)

        if new_jobs:
            print(f'  {company} — {len(new_jobs)} NEW posting(s):')
            for job_url, title in new_jobs:
                print(f'    ★ {title}')
                print(f'      {job_url}')
                if update_seen:
                    normalized = re.sub(r'[?#].*', '', job_url).rstrip('/')
                    checked_urls[normalized] = {
                        'title': title,
                        'company': company,
                        'first_seen': today,
                        'last_seen': today,
                    }

        if verbose and seen_jobs:
            print(f'  {company} — {len(seen_jobs)} previously seen:')
            for job_url, title in seen_jobs:
                print(f'    · {title}')
                print(f'      {job_url}')

        # Update last_seen for already-known jobs
        if update_seen:
            for job_url, title in seen_jobs:
                normalized = re.sub(r'[?#].*', '', job_url).rstrip('/')
                if normalized in checked_urls:
                    checked_urls[normalized]['last_seen'] = today
                else:
                    checked_urls[normalized] = {
                        'title': title,
                        'company': company,
                        'first_seen': today,
                        'last_seen': today,
                    }

        if not new_jobs and not verbose:
            if not jobs:
                print(f'  {company} — no matching jobs found')
            else:
                print(f'  {company} — {len(seen_jobs)} jobs (all previously seen)')

    # Summary
    print(f'\n  New: {new_total}  |  Previously seen: {seen_total}  |'
          f'  Errors: {len(error_pages)}')

    if error_pages:
        print('\n  Pages with errors:')
        for company, error in error_pages:
            print(f'    {company}: {error}')

    if update_seen:
        config['checked_urls'] = checked_urls
        save_config(config)
        print(f'\n  Updated checked_urls with {new_total + seen_total} entries.')
    elif new_total > 0:
        print(f'\n  Run with --update-seen to mark these as reviewed.')


def show_queries(config):
    """Print stored search queries for manual re-running."""
    queries = config.get('search_queries', [])
    if not queries:
        print('No search queries configured.')
        return

    print(f'\nSaved search queries ({len(queries)}):')
    print('Copy these into your search engine or use with Claude.\n')
    for i, q in enumerate(queries, 1):
        print(f'  {i:2d}. {q}')

    filters = config.get('filters', {})
    if filters:
        print('\nFilter criteria (for reference):')
        for key, val in filters.items():
            print(f'  {key}: {val}')


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Scan career pages for new job postings',
    )
    parser.add_argument(
        '--show-queries', action='store_true',
        help='Print saved search queries for manual re-running',
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Show all checked URLs, not just new ones',
    )
    parser.add_argument(
        '--update-seen', action='store_true',
        help='Mark all current postings as "seen" in the config',
    )
    parser.add_argument(
        '--workers', type=int, default=5,
        help='Number of parallel fetches (default: 5)',
    )
    args = parser.parse_args()

    if not CONFIG_FILE.exists():
        print(f'Error: {CONFIG_FILE} not found', file=sys.stderr)
        print('Create job_search_config.json with your career pages and queries.',
              file=sys.stderr)
        sys.exit(1)

    config = load_config()

    run_scan(config, verbose=args.verbose, update_seen=args.update_seen)

    if args.show_queries:
        show_queries(config)


if __name__ == '__main__':
    main()
