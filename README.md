# Job Search Tracker

A self-hosted web application and CLI tool for managing your job search. Track applications, manage tailored resumes and cover letters, monitor follow-ups, and view stats -- all from a local Flask dashboard or the command line.

## Features

- **Dashboard** with application statistics, response rates, and upcoming follow-ups
- **Job list** with filtering by status, priority, and group; sortable columns
- **Job detail** pages with linked resume/cover letter per company
- **Document viewer** to preview markdown resumes and cover letters in the browser
- **Add/edit/delete/hide** jobs through the web UI
- **CLI tool** (`update_tracker.py`) for quick terminal-based updates
- **Resume converter** to produce ATS-friendly DOCX and PDF from markdown
- **Cover letter converter** with professional PDF formatting
- **CSV-based storage** -- no database required, easy to back up and version

## Quick Start

### 1. Clone and install

```bash
git clone git@github.com:brettburan/jobsearch.git
cd jobsearch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Set your name so resume/cover letter file patterns are detected correctly:

```bash
export CANDIDATE_NAME="Jane_Doe"           # FirstName_LastName, underscores
export BASE_RESUME_FILENAME="Jane_Doe_Resume.pdf"  # optional
```

Or create a `.env` file (the app reads environment variables):

```
CANDIDATE_NAME=Jane_Doe
BASE_RESUME_FILENAME=Jane_Doe_Resume.pdf
```

### 3. Set up your data

```bash
# Create directories for your documents
mkdir -p Resumes CoverLetters

# Copy the example CSV to get started
cp job_tracker.example.csv job_tracker.csv
```

### 4. Run the web app

```bash
cd webapp
python3 run.py
```

Open http://localhost:5000 in your browser.

### 5. Or use the CLI

```bash
python3 update_tracker.py              # Interactive mode
python3 update_tracker.py --list       # Show all jobs
python3 update_tracker.py --stats      # Application statistics
python3 update_tracker.py --followups  # Upcoming follow-ups
```

## File Naming Convention

The tracker expects resumes and cover letters to follow this pattern:

```
Resumes/{CANDIDATE_NAME}_Resume_{Company}.md
CoverLetters/{CANDIDATE_NAME}_CoverLetter_{Company}.md
```

For example, if `CANDIDATE_NAME=Jane_Doe` and you're applying to Acme Corp:

```
Resumes/Jane_Doe_Resume_Acme_Corp.md
CoverLetters/Jane_Doe_CoverLetter_Acme_Corp.md
```

The company name in the filename should match the "Company" column in the CSV with spaces replaced by underscores.

## Converting Documents

```bash
source .venv/bin/activate

# Convert all resumes to DOCX (ATS-friendly)
python3 convert_resumes.py --all

# Convert a single resume
python3 convert_resumes.py Resumes/Jane_Doe_Resume_Acme_Corp.md

# Convert to PDF instead
python3 convert_resumes.py --all --pdf

# Convert cover letters to PDF
python3 convert_coverletters.py
```

## Project Structure

```
jobsearch/
├── webapp/
│   ├── app.py              # Flask routes
│   ├── tracker.py          # Data layer (CSV read/write, stats, document listing)
│   ├── config.py           # Configuration (candidate name, file patterns)
│   ├── run.py              # App entry point
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── jobs.html
│   │   ├── job_detail.html
│   │   ├── job_form.html
│   │   ├── documents.html
│   │   └── document_view.html
│   └── static/
│       └── style.css
├── update_tracker.py       # CLI tracker tool
├── convert_resumes.py      # Markdown to DOCX/PDF converter
├── convert_coverletters.py # Cover letter converter
├── job_tracker.example.csv # Example CSV with sample data
├── examples/
│   ├── Example_Resume.md       # Sample resume format
│   └── Example_CoverLetter.md  # Sample cover letter format
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## CSV Columns

| Column | Description |
|--------|-------------|
| Company | Company name |
| Position | Job title |
| Location | Remote / Hybrid / City |
| Salary (Base) | Base salary range |
| Total Comp Est. | Total compensation estimate |
| Status | Application status (see below) |
| Applied Date | Date application submitted (YYYY-MM-DD) |
| Job URL | Link to job posting |
| Contact Name | Recruiter or hiring manager |
| Contact Email | Contact email |
| Contact Phone | Contact phone |
| Last Contact Date | Most recent communication |
| Next Follow-Up | Scheduled follow-up date |
| Interview Stage | Current interview stage |
| Notes | Timestamped notes (appended automatically) |
| Priority | Critical / High / Medium / Low |
| Hidden | "yes" to hide from default views |

### Status Values

Not Applied, Applied, Phone Screen Scheduled, Phone Screen Complete, Technical Interview Scheduled, Technical Interview Complete, On-Site/Virtual Interview Scheduled, On-Site/Virtual Interview Complete, Offer Received, Offer Accepted, Offer Declined, Rejected, Withdrawn, No Response, Position Closed

## Using with Claude Code

This project includes a `CLAUDE.md` file that gives [Claude Code](https://docs.anthropic.com/en/docs/claude-code) context about the codebase. With Claude Code you can manage your job search conversationally:

- **Add jobs**: "Add a Senior Security Engineer position at Acme Corp, remote, $200k-$250k base"
- **Tailor resumes**: "Create a resume for the Acme Corp position emphasizing cloud security and Python"
- **Write cover letters**: "Write a cover letter for Acme Corp that highlights my penetration testing experience"
- **Update status**: "Mark the Acme Corp application as applied with today's date"
- **Research**: "Find the job posting URL for this position and add it to the tracker"

### Setup

1. Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
2. Run `claude` from the project root
3. Claude will automatically read `CLAUDE.md` for project context

### Customizing CLAUDE.md

Edit `CLAUDE.md` to add your own context that helps Claude assist you:

- Your background and target roles
- Job search criteria (location, salary, work arrangement)
- Resume emphasis areas per company type
- Any terminology translations (e.g., government to commercial language)

`CLAUDE.md` is tracked by git, so keep personal details (phone, email, clearance status) out of it -- or add it to `.gitignore` if you want a fully private version.

## Pre-Commit Safety Hook

The repo includes a pre-commit hook (`.githooks/pre-commit`) that scans staged files for personal data patterns before allowing a commit. To set it up:

```bash
# Configure git to use the hooks directory
git config core.hooksPath .githooks

# Edit the hook to add your personal patterns
# (phone number, email, employer name, etc.)
nano .githooks/pre-commit
```

Add your patterns to the `PATTERNS` array in the hook:

```bash
PATTERNS=(
    "555-123-4567"
    "janedoe@example\\.com"
    "My Employer Name"
)
```

Any commit containing those strings will be blocked with a clear error message. To bypass intentionally: `git commit --no-verify`.

## License

MIT -- see [LICENSE](LICENSE).
