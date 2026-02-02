"""
Data access layer for job_tracker.csv.
Shared constants, CSV read/write, stats computation, and document listing.
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path

from config import RESUME_PREFIX, COVER_LETTER_PREFIX, WHY_COMPANY_PREFIX

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRACKER_FILE = PROJECT_ROOT / 'job_tracker.csv'
RESUMES_DIR = PROJECT_ROOT / 'Resumes'
COVERLETTERS_DIR = PROJECT_ROOT / 'CoverLetters'
WHYCOMPANY_DIR = PROJECT_ROOT / 'WhyCompany'

FIELDNAMES = [
    'Company', 'Position', 'Location', 'Salary (Base)', 'Total Comp Est.',
    'Status', 'Applied Date', 'Job URL', 'Contact Name', 'Contact Email',
    'Contact Phone', 'Last Contact Date', 'Next Follow-Up', 'Interview Stage',
    'Notes', 'Priority', 'Hidden', 'Hide Reason',
]

HIDE_REASONS = [
    'Not a Good Fit',
    'Bad Location',
    'Low Compensation',
    'Position Closed',
    'Bad Reviews',
    'Other',
]

VALID_STATUSES = [
    'Not Applied', 'Applied', 'Phone Screen Scheduled', 'Phone Screen Complete',
    'Technical Interview Scheduled', 'Technical Interview Complete',
    'On-Site/Virtual Interview Scheduled', 'On-Site/Virtual Interview Complete',
    'Offer Received', 'Offer Accepted', 'Offer Declined',
    'Rejected', 'Withdrawn', 'No Response', 'Position Closed',
]

INTERVIEW_STAGES = [
    'None', 'Recruiter Screen', 'Hiring Manager Screen', 'Technical Phone',
    'Take-Home Assessment', 'Virtual On-Site', 'In-Person On-Site',
    'Final Round', 'Team Match', 'Offer Stage', 'Negotiation',
]

PRIORITY_ORDER = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}


def load_jobs():
    """Load all jobs from CSV. Returns list of dicts, skipping empty rows."""
    if not TRACKER_FILE.exists():
        return []
    with open(TRACKER_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        jobs = []
        for row in reader:
            if not row.get('Company', '').strip():
                continue
            # Strip keys not in FIELDNAMES (e.g. None from extra CSV columns)
            cleaned = {k: v for k, v in row.items() if k in FIELDNAMES}
            # Ensure all fields exist
            for field in FIELDNAMES:
                if field not in cleaned:
                    cleaned[field] = ''
            jobs.append(cleaned)
        return jobs


def save_jobs(rows):
    """Write jobs back to CSV, preserving the standard field order."""
    with open(TRACKER_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def get_job(index):
    """Get a single job by 0-based index. Returns (job_dict, index) or (None, None)."""
    jobs = load_jobs()
    if 0 <= index < len(jobs):
        return jobs[index], index
    return None, None


def add_job(data):
    """Add a new job from form data dict. Returns the new job."""
    jobs = load_jobs()
    row = {f: '' for f in FIELDNAMES}
    for field in FIELDNAMES:
        if field in data:
            row[field] = data[field].strip()
    if not row['Status']:
        row['Status'] = 'Not Applied'
    # Auto-set follow-up when applied date is set
    if row['Applied Date'] and not row['Next Follow-Up']:
        try:
            d = datetime.strptime(row['Applied Date'], '%Y-%m-%d')
            row['Next Follow-Up'] = (d + timedelta(days=7)).strftime('%Y-%m-%d')
        except ValueError:
            pass
    if row['Applied Date'] and row['Status'] == 'Not Applied':
        row['Status'] = 'Applied'
    jobs.append(row)
    save_jobs(jobs)
    return row


def update_job(index, data):
    """Update job at 0-based index with form data. Returns updated job or None."""
    jobs = load_jobs()
    if not (0 <= index < len(jobs)):
        return None
    row = jobs[index]
    for field in FIELDNAMES:
        if field in data:
            val = data[field].strip()
            if field == 'Notes' and val:
                existing = row.get('Notes', '')
                if existing:
                    row['Notes'] = f"{existing} | {datetime.now().strftime('%m/%d')}: {val}"
                else:
                    row['Notes'] = f"{datetime.now().strftime('%m/%d')}: {val}"
            else:
                row[field] = val
    # Auto-set follow-up when applied date changes
    if data.get('Applied Date') and not row.get('Next Follow-Up'):
        try:
            d = datetime.strptime(row['Applied Date'], '%Y-%m-%d')
            row['Next Follow-Up'] = (d + timedelta(days=7)).strftime('%Y-%m-%d')
        except ValueError:
            pass
    if row['Applied Date'] and row['Status'] == 'Not Applied':
        row['Status'] = 'Applied'
    save_jobs(jobs)
    return row


def delete_job(index):
    """Delete job at 0-based index. Returns True if deleted."""
    jobs = load_jobs()
    if not (0 <= index < len(jobs)):
        return False
    jobs.pop(index)
    save_jobs(jobs)
    return True


def hide_job(index, reason=''):
    """Hide job at 0-based index. Returns True if hidden."""
    jobs = load_jobs()
    if not (0 <= index < len(jobs)):
        return False
    jobs[index]['Hidden'] = 'yes'
    jobs[index]['Hide Reason'] = reason
    save_jobs(jobs)
    return True


def unhide_job(index):
    """Unhide job at 0-based index. Returns True if unhidden."""
    jobs = load_jobs()
    if not (0 <= index < len(jobs)):
        return False
    jobs[index]['Hidden'] = ''
    jobs[index]['Hide Reason'] = ''
    save_jobs(jobs)
    return True


def compute_stats():
    """Compute dashboard statistics. Returns dict. Excludes hidden jobs."""
    jobs = [j for j in load_jobs() if j.get('Hidden', '').lower() != 'yes']
    total = len(jobs)
    applied = sum(1 for r in jobs if r.get('Status') != 'Not Applied')
    not_applied = sum(1 for r in jobs if r.get('Status') == 'Not Applied')
    interviewing = sum(1 for r in jobs if 'Interview' in r.get('Status', '') or 'Screen' in r.get('Status', ''))
    offers = sum(1 for r in jobs if 'Offer' in r.get('Status', ''))
    rejected = sum(1 for r in jobs if r.get('Status') in ('Rejected', 'No Response', 'Position Closed'))
    response_rate = f"{((interviewing + offers) / applied * 100):.0f}%" if applied > 0 else "N/A"

    return {
        'total': total,
        'applied': applied,
        'not_applied': not_applied,
        'interviewing': interviewing,
        'offers': offers,
        'rejected': rejected,
        'response_rate': response_rate,
    }


def get_followups():
    """Get jobs with upcoming follow-ups, sorted by date. Excludes hidden jobs."""
    jobs = [j for j in load_jobs() if j.get('Hidden', '').lower() != 'yes']
    followups = [r for r in jobs if r.get('Next Follow-Up')]
    followups.sort(key=lambda r: r.get('Next Follow-Up', ''))
    # Attach original index for linking
    all_jobs = load_jobs()
    for fu in followups:
        for i, j in enumerate(all_jobs):
            if j is fu:
                fu['_index'] = i
                break
    return followups


def list_documents():
    """List all resume and cover letter files. Returns dict with 'resumes' and 'cover_letters'."""
    resumes = []
    cover_letters = []
    if RESUMES_DIR.exists():
        for f in sorted(RESUMES_DIR.iterdir()):
            if f.suffix in ('.md', '.pdf'):
                company = f.stem.replace(RESUME_PREFIX, '')
                resumes.append({
                    'filename': f.name,
                    'company': company,
                    'type': f.suffix[1:],
                    'path': str(f),
                })
    if COVERLETTERS_DIR.exists():
        for f in sorted(COVERLETTERS_DIR.iterdir()):
            if f.suffix in ('.md', '.pdf'):
                company = f.stem.replace(COVER_LETTER_PREFIX, '')
                cover_letters.append({
                    'filename': f.name,
                    'company': company,
                    'type': f.suffix[1:],
                    'path': str(f),
                })
    return {'resumes': resumes, 'cover_letters': cover_letters}


def _normalize(text):
    """Strip to lowercase alphanumeric for fuzzy matching."""
    import re
    return re.sub(r'[^a-z0-9]', '', text.lower())


def _filter_by_position(docs, company, position, prefix_len):
    """Narrow a list of document dicts to those whose filename suffix matches
    the position.  Falls back to the full list if nothing matches."""
    if len(docs) <= 1 or not position:
        return docs
    norm_pos = _normalize(position)
    norm_company = _normalize(company)
    matched = []
    for doc in docs:
        # Role-specific part of the filename (e.g. "Safeguards" from
        # "Anthropic_Safeguards")
        role_suffix = _normalize(doc['company'][len(norm_company):])
        if role_suffix and role_suffix in norm_pos:
            matched.append(doc)
    return matched


def get_company_documents(company, position=''):
    """Find resume and cover letter files matching a company name.

    Uses glob matching so that companies with multiple positions (e.g.,
    Anthropic_Safeguards + Anthropic_FrontierRedTeam) are all discovered.
    When *position* is provided and there are multiple matches, narrows
    results to files whose role suffix appears in the position title.
    Returns dict with 'resumes' and 'cover_letters' keys, each a list of
    dicts with md_path/pdf_name/label.
    """
    result = {'resumes': [], 'cover_letters': [], 'why_company': []}
    if not company:
        return result

    variants = [
        company.replace(' ', '_'),
        company.replace(' ', ''),
    ]

    for suffix in variants:
        for md_path in sorted(RESUMES_DIR.glob(f'{RESUME_PREFIX}{suffix}*.md')):
            stem = md_path.stem
            tag = stem[len(RESUME_PREFIX):]
            result['resumes'].append({
                'md_path': str(md_path),
                'pdf_name': f'{stem}.pdf',
                'company': tag,
                'label': tag.replace('_', ' '),
            })
        if result['resumes']:
            break

    for suffix in variants:
        for md_path in sorted(COVERLETTERS_DIR.glob(f'{COVER_LETTER_PREFIX}{suffix}*.md')):
            stem = md_path.stem
            tag = stem[len(COVER_LETTER_PREFIX):]
            result['cover_letters'].append({
                'md_path': str(md_path),
                'pdf_name': f'{stem}.pdf',
                'company': tag,
                'label': tag.replace('_', ' '),
            })
        if result['cover_letters']:
            break

    if WHYCOMPANY_DIR.exists():
        for suffix in variants:
            for md_path in sorted(WHYCOMPANY_DIR.glob(f'{WHY_COMPANY_PREFIX}{suffix}*.md')):
                stem = md_path.stem
                tag = stem[len(WHY_COMPANY_PREFIX):]
                result['why_company'].append({
                    'md_path': str(md_path),
                    'company': tag,
                    'label': tag.replace('_', ' '),
                })
            if result['why_company']:
                break

    result['resumes'] = _filter_by_position(
        result['resumes'], company, position, len(RESUME_PREFIX))
    result['cover_letters'] = _filter_by_position(
        result['cover_letters'], company, position, len(COVER_LETTER_PREFIX))
    result['why_company'] = _filter_by_position(
        result['why_company'], company, position, len(WHY_COMPANY_PREFIX))

    return result


def read_markdown(filepath):
    """Read a markdown file and return raw text. Returns None if not found."""
    p = Path(filepath)
    if not p.exists() or p.suffix != '.md':
        return None
    return p.read_text(encoding='utf-8')
