#!/usr/bin/env python3
"""
Job Application Tracker - Interactive CLI for updating job_tracker.csv

Usage:
    python3 update_tracker.py                  # Interactive mode
    python3 update_tracker.py --list           # Show all jobs and status
    python3 update_tracker.py --applied        # Show only applied jobs
    python3 update_tracker.py --pending        # Show jobs not yet applied to
    python3 update_tracker.py --followups      # Show upcoming follow-ups
    python3 update_tracker.py --stats          # Show application statistics
"""

import csv
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

TRACKER_FILE = Path(__file__).parent / 'job_tracker.csv'

VALID_STATUSES = [
    'Not Applied',
    'Applied',
    'Phone Screen Scheduled',
    'Phone Screen Complete',
    'Technical Interview Scheduled',
    'Technical Interview Complete',
    'On-Site/Virtual Interview Scheduled',
    'On-Site/Virtual Interview Complete',
    'Offer Received',
    'Offer Accepted',
    'Offer Declined',
    'Rejected',
    'Withdrawn',
    'No Response',
    'Position Closed',
]

INTERVIEW_STAGES = [
    'None',
    'Recruiter Screen',
    'Hiring Manager Screen',
    'Technical Phone',
    'Take-Home Assessment',
    'Virtual On-Site',
    'In-Person On-Site',
    'Final Round',
    'Team Match',
    'Offer Stage',
    'Negotiation',
]


def load_tracker():
    """Load the CSV tracker into a list of dicts."""
    if not TRACKER_FILE.exists():
        print(f"Tracker file not found: {TRACKER_FILE}")
        sys.exit(1)
    with open(TRACKER_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def save_tracker(rows, fieldnames):
    """Save the list of dicts back to CSV."""
    with open(TRACKER_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nTracker saved to {TRACKER_FILE}")


def display_jobs(rows, title="All Jobs"):
    """Display jobs in a formatted table."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")
    for i, row in enumerate(rows):
        status_icon = {
            'Not Applied': '⬜',
            'Applied': '📨',
            'Phone Screen Scheduled': '📞',
            'Phone Screen Complete': '✅📞',
            'Technical Interview Scheduled': '💻',
            'Technical Interview Complete': '✅💻',
            'On-Site/Virtual Interview Scheduled': '🏢',
            'On-Site/Virtual Interview Complete': '✅🏢',
            'Offer Received': '🎉',
            'Offer Accepted': '🥳',
            'Offer Declined': '❌',
            'Rejected': '🚫',
            'Withdrawn': '🔙',
            'No Response': '😶',
            'Position Closed': '🔒',
        }.get(row.get('Status', ''), '❓')

        print(f"  [{i+1}] {status_icon} {row.get('Company', 'Unknown')} - {row.get('Position', 'Unknown')}")
        print(f"      Location: {row.get('Location', 'N/A')} | Salary: {row.get('Total Comp Est.', 'N/A')} | Priority: {row.get('Priority', 'N/A')}")
        print(f"      Status: {row.get('Status', 'N/A')}", end='')
        if row.get('Applied Date'):
            print(f" | Applied: {row['Applied Date']}", end='')
        if row.get('Interview Stage') and row['Interview Stage'] != 'None':
            print(f" | Stage: {row['Interview Stage']}", end='')
        if row.get('Contact Name'):
            print(f" | Contact: {row['Contact Name']}", end='')
        if row.get('Next Follow-Up'):
            print(f" | Follow-Up: {row['Next Follow-Up']}", end='')
        print()
        if row.get('Notes'):
            notes = row['Notes'][:80] + '...' if len(row.get('Notes', '')) > 80 else row.get('Notes', '')
            print(f"      Notes: {notes}")
        print()


def display_stats(rows):
    """Show application statistics."""
    total = len(rows)
    applied = sum(1 for r in rows if r.get('Status') != 'Not Applied')
    not_applied = sum(1 for r in rows if r.get('Status') == 'Not Applied')
    interviewing = sum(1 for r in rows if 'Interview' in r.get('Status', '') or 'Screen' in r.get('Status', ''))
    offers = sum(1 for r in rows if 'Offer' in r.get('Status', ''))
    rejected = sum(1 for r in rows if r.get('Status') in ('Rejected', 'No Response', 'Position Closed'))

    print(f"\n{'='*50}")
    print(f"  APPLICATION STATISTICS")
    print(f"{'='*50}")
    print(f"  Total jobs tracked:     {total}")
    print(f"  Applied:                {applied}")
    print(f"  Not yet applied:        {not_applied}")
    print(f"  Interviewing:           {interviewing}")
    print(f"  Offers:                 {offers}")
    print(f"  Rejected/No Response:   {rejected}")
    if applied > 0:
        print(f"  Response rate:          {((interviewing + offers) / applied * 100):.0f}%")
    print(f"{'='*50}\n")


def display_followups(rows):
    """Show upcoming follow-ups."""
    followups = [r for r in rows if r.get('Next Follow-Up')]
    if not followups:
        print("\nNo follow-ups scheduled.")
        return
    followups.sort(key=lambda r: r.get('Next Follow-Up', ''))
    print(f"\n{'='*60}")
    print(f"  UPCOMING FOLLOW-UPS")
    print(f"{'='*60}\n")
    for r in followups:
        print(f"  {r['Next Follow-Up']} - {r['Company']} ({r['Position']})")
        if r.get('Contact Name'):
            contact = r['Contact Name']
            if r.get('Contact Email'):
                contact += f" <{r['Contact Email']}>"
            print(f"    Contact: {contact}")
        print()


def update_job(rows, fieldnames):
    """Interactive update for a specific job."""
    display_jobs(rows)
    try:
        idx = int(input("Enter job number to update (0 to cancel): ")) - 1
        if idx < 0 or idx >= len(rows):
            print("Cancelled.")
            return rows
    except (ValueError, EOFError):
        print("Cancelled.")
        return rows

    row = rows[idx]
    print(f"\nUpdating: {row['Company']} - {row['Position']}")
    print(f"Current Status: {row.get('Status', 'N/A')}\n")

    print("What would you like to update?")
    print("  1. Status (applied, interview, offer, etc.)")
    print("  2. Applied Date")
    print("  3. Contact Info (name, email, phone)")
    print("  4. Last Contact Date")
    print("  5. Next Follow-Up Date")
    print("  6. Interview Stage")
    print("  7. Notes")
    print("  8. Multiple fields at once")
    print("  0. Cancel")

    try:
        choice = input("\nChoice: ").strip()
    except EOFError:
        return rows

    if choice == '0':
        return rows

    elif choice == '1':
        print("\nAvailable statuses:")
        for i, s in enumerate(VALID_STATUSES):
            print(f"  {i+1}. {s}")
        try:
            si = int(input("Enter status number: ")) - 1
            if 0 <= si < len(VALID_STATUSES):
                row['Status'] = VALID_STATUSES[si]
                print(f"Status updated to: {row['Status']}")
        except (ValueError, EOFError):
            pass

    elif choice == '2':
        date = input("Applied date (YYYY-MM-DD, or press Enter for today): ").strip()
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        row['Applied Date'] = date
        if row.get('Status') == 'Not Applied':
            row['Status'] = 'Applied'
        # Auto-set follow-up to 1 week later
        try:
            follow_date = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            row['Next Follow-Up'] = follow_date
            print(f"Applied: {date} | Auto-set follow-up: {follow_date}")
        except ValueError:
            row['Applied Date'] = date
            print(f"Applied: {date}")

    elif choice == '3':
        name = input("Contact name (Enter to skip): ").strip()
        if name:
            row['Contact Name'] = name
        email = input("Contact email (Enter to skip): ").strip()
        if email:
            row['Contact Email'] = email
        phone = input("Contact phone (Enter to skip): ").strip()
        if phone:
            row['Contact Phone'] = phone
        print("Contact info updated.")

    elif choice == '4':
        date = input("Last contact date (YYYY-MM-DD, or Enter for today): ").strip()
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        row['Last Contact Date'] = date
        print(f"Last contact: {date}")

    elif choice == '5':
        date = input("Next follow-up date (YYYY-MM-DD): ").strip()
        row['Next Follow-Up'] = date
        print(f"Follow-up set: {date}")

    elif choice == '6':
        print("\nInterview stages:")
        for i, s in enumerate(INTERVIEW_STAGES):
            print(f"  {i+1}. {s}")
        try:
            si = int(input("Enter stage number: ")) - 1
            if 0 <= si < len(INTERVIEW_STAGES):
                row['Interview Stage'] = INTERVIEW_STAGES[si]
                print(f"Interview stage: {row['Interview Stage']}")
        except (ValueError, EOFError):
            pass

    elif choice == '7':
        note = input("Add note (will append to existing): ").strip()
        if note:
            existing = row.get('Notes', '')
            if existing:
                row['Notes'] = f"{existing} | {datetime.now().strftime('%m/%d')}: {note}"
            else:
                row['Notes'] = f"{datetime.now().strftime('%m/%d')}: {note}"
            print("Note added.")

    elif choice == '8':
        # Quick multi-field update
        print("\nQuick update - press Enter to skip any field:\n")

        date = input("  Applied date (YYYY-MM-DD or Enter for today, 's' to skip): ").strip()
        if date and date != 's':
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            row['Applied Date'] = date
            if row.get('Status') == 'Not Applied':
                row['Status'] = 'Applied'
            try:
                follow = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
                row['Next Follow-Up'] = follow
            except ValueError:
                pass

        name = input("  Contact name (Enter to skip): ").strip()
        if name:
            row['Contact Name'] = name

        email = input("  Contact email (Enter to skip): ").strip()
        if email:
            row['Contact Email'] = email

        print("\n  Status options:")
        for i, s in enumerate(VALID_STATUSES):
            print(f"    {i+1}. {s}")
        status = input("  Status number (Enter to skip): ").strip()
        if status:
            try:
                si = int(status) - 1
                if 0 <= si < len(VALID_STATUSES):
                    row['Status'] = VALID_STATUSES[si]
            except ValueError:
                pass

        note = input("  Note (Enter to skip): ").strip()
        if note:
            existing = row.get('Notes', '')
            if existing:
                row['Notes'] = f"{existing} | {datetime.now().strftime('%m/%d')}: {note}"
            else:
                row['Notes'] = f"{datetime.now().strftime('%m/%d')}: {note}"

        print("\nUpdated!")

    return rows


def add_job(rows, fieldnames):
    """Add a new job to the tracker."""
    print("\nAdd New Job\n")
    row = {f: '' for f in fieldnames}

    row['Company'] = input("Company name: ").strip()
    row['Position'] = input("Position title: ").strip()
    row['Location'] = input("Location (e.g., Remote US, Hybrid - Herndon VA): ").strip()
    row['Salary (Base)'] = input("Base salary range (e.g., $180k-$250k): ").strip()
    row['Total Comp Est.'] = input("Total comp estimate (e.g., $200k-$300k): ").strip()
    row['Job URL'] = input("Job URL: ").strip()
    row['Priority'] = input("Priority (Critical/High/Medium/Low): ").strip() or 'Medium'
    row['Notes'] = input("Notes: ").strip()
    row['Status'] = 'Not Applied'

    applied = input("Already applied? (y/n): ").strip().lower()
    if applied == 'y':
        date = input("Applied date (YYYY-MM-DD, Enter for today): ").strip()
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        row['Applied Date'] = date
        row['Status'] = 'Applied'
        try:
            row['Next Follow-Up'] = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        except ValueError:
            pass

    rows.append(row)
    print(f"\nAdded: {row['Company']} - {row['Position']}")
    return rows


def main():
    rows, fieldnames = load_tracker()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--list':
            display_jobs(rows)
        elif arg == '--applied':
            applied = [r for r in rows if r.get('Status') != 'Not Applied']
            display_jobs(applied, "Applied Jobs")
        elif arg == '--pending':
            pending = [r for r in rows if r.get('Status') == 'Not Applied']
            display_jobs(pending, "Pending Applications")
        elif arg == '--followups':
            display_followups(rows)
        elif arg == '--stats':
            display_stats(rows)
        elif arg == '--help':
            print(__doc__)
        return

    # Interactive mode
    while True:
        print(f"\n{'='*50}")
        print("  JOB APPLICATION TRACKER")
        print(f"{'='*50}")
        print("  1. View all jobs")
        print("  2. View pending (not applied)")
        print("  3. View applied jobs")
        print("  4. View follow-ups")
        print("  5. View statistics")
        print("  6. Update a job")
        print("  7. Add a new job")
        print("  8. Save & exit")
        print("  0. Exit without saving")

        try:
            choice = input("\nChoice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if choice == '1':
            display_jobs(rows)
        elif choice == '2':
            pending = [r for r in rows if r.get('Status') == 'Not Applied']
            display_jobs(pending, "Pending Applications")
        elif choice == '3':
            applied = [r for r in rows if r.get('Status') != 'Not Applied']
            display_jobs(applied, "Applied Jobs")
        elif choice == '4':
            display_followups(rows)
        elif choice == '5':
            display_stats(rows)
        elif choice == '6':
            rows = update_job(rows, fieldnames)
        elif choice == '7':
            rows = add_job(rows, fieldnames)
        elif choice == '8':
            save_tracker(rows, fieldnames)
            print("Goodbye!")
            break
        elif choice == '0':
            print("Exiting without saving.")
            break


if __name__ == '__main__':
    main()
