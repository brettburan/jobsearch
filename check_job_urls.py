#!/usr/bin/env python3
"""
Job URL Checker - Verify whether tracked job postings are still active.

Fetches each job's URL and checks for signals that the posting has been
closed, removed, or expired.

Usage:
    python3 check_job_urls.py              # Check all non-closed jobs
    python3 check_job_urls.py --all        # Check every job, including closed
    python3 check_job_urls.py --update     # Automatically mark closed jobs
    python3 check_job_urls.py --verbose    # Show details for each check
"""

import argparse
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TRACKER_FILE = Path(__file__).parent / 'job_tracker.csv'

# Patterns in page content that indicate a posting is no longer active.
CLOSED_PATTERNS = re.compile(
    r'no longer (available|accepting|open)'
    r'|position.{0,20}(has been |been )?(filled|closed|removed)'
    r'|job.{0,20}(has been |been )?(closed|expired|removed|no longer)'
    r'|this role has been'
    r'|this (job|position) (is|has) (no longer|been)'
    r'|page\s*not\s*found'
    r"|we couldn.?t find"
    r'|does not exist'
    r'|posting has been'
    r'|opening is no longer'
    r'|not currently accepting'
    r'|no matching job'
    r'|job not found'
    r'|this listing has'
    r'|opportunity is no longer',
    re.IGNORECASE,
)


def fetch_url(url, timeout=15):
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
            capture_output=True, text=True, timeout=timeout + 5,
        )
        output = result.stdout
        code_match = re.search(r'__HTTP_CODE__:(\d+)', output)
        http_code = int(code_match.group(1)) if code_match else 0
        body = output[:output.rfind('__HTTP_CODE__:')] if code_match else output
        return http_code, body
    except (subprocess.TimeoutExpired, Exception) as e:
        return 0, str(e)


def check_posting(url):
    """Check a single URL. Returns (status_str, detail)."""
    if not url or not url.startswith('http'):
        return 'NO_URL', 'No valid URL provided'

    http_code, body = fetch_url(url)

    if http_code == 0:
        return 'UNREACHABLE', 'Connection failed or timed out'
    if http_code == 404:
        return 'CLOSED', f'HTTP 404 - page not found'
    if http_code == 403:
        return 'BLOCKED', f'HTTP 403 - site blocks automated access'
    if http_code >= 400:
        return 'ERROR', f'HTTP {http_code}'

    if CLOSED_PATTERNS.search(body):
        return 'CLOSED', 'Page content indicates posting is closed'

    return 'OPEN', f'HTTP {http_code} - no closed signals detected'


def load_tracker():
    """Read job_tracker.csv and return (fieldnames, rows)."""
    with open(TRACKER_FILE, newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def save_tracker(fieldnames, rows):
    """Write rows back to job_tracker.csv."""
    with open(TRACKER_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Check job posting URLs')
    parser.add_argument('--all', action='store_true',
                        help='Check all jobs, including already-closed ones')
    parser.add_argument('--update', action='store_true',
                        help='Automatically mark closed jobs in the CSV')
    parser.add_argument('--verbose', action='store_true',
                        help='Show details for every job checked')
    parser.add_argument('--workers', type=int, default=5,
                        help='Number of parallel checks (default: 5)')
    args = parser.parse_args()

    if not TRACKER_FILE.exists():
        print(f'Error: {TRACKER_FILE} not found', file=sys.stderr)
        sys.exit(1)

    fieldnames, rows = load_tracker()

    # Filter rows to check
    jobs_to_check = []
    for i, row in enumerate(rows):
        status = row.get('Status', '').strip()
        url = row.get('Job URL', '').strip()
        if not args.all and status == 'Position Closed':
            continue
        if not url:
            continue
        jobs_to_check.append((i, row, url))

    if not jobs_to_check:
        print('No jobs to check.')
        return

    print(f'Checking {len(jobs_to_check)} job URLs...\n')

    # Check URLs in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(check_posting, url): (i, row)
            for i, row, url in jobs_to_check
        }
        for future in as_completed(futures):
            idx, row = futures[future]
            status_str, detail = future.result()
            results[idx] = (status_str, detail)

    # Report results
    closed_count = 0
    open_count = 0
    blocked_count = 0

    for i, row, url in sorted(jobs_to_check, key=lambda x: x[0]):
        status_str, detail = results[i]
        company = row.get('Company', '').strip()
        position = row.get('Position', '').strip()
        label = f'{company} - {position}'

        if status_str == 'CLOSED':
            closed_count += 1
            print(f'  CLOSED  {label}')
            if args.verbose:
                print(f'          {detail}')
            if args.update:
                rows[i]['Status'] = 'Position Closed'
        elif status_str == 'OPEN':
            open_count += 1
            if args.verbose:
                print(f'  OPEN    {label}')
                print(f'          {detail}')
        elif status_str == 'BLOCKED':
            blocked_count += 1
            if args.verbose:
                print(f'  ???     {label}')
                print(f'          {detail}')
        else:
            blocked_count += 1
            if args.verbose:
                print(f'  ???     {label}')
                print(f'          {detail}')

    print(f'\n  Open: {open_count}  |  Closed: {closed_count}  |'
          f'  Could not verify: {blocked_count}')

    if args.update and closed_count > 0:
        save_tracker(fieldnames, rows)
        print(f'\nUpdated {closed_count} jobs to "Position Closed" in {TRACKER_FILE.name}')
    elif closed_count > 0 and not args.update:
        print(f'\nRun with --update to mark closed jobs in the CSV.')


if __name__ == '__main__':
    main()
