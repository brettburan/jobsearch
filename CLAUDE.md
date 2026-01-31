# Job Search Tracker - Project Instructions

## Overview
A Flask web app + CLI tool for tracking job applications. CSV-based storage, markdown resume/cover letter management, DOCX/PDF conversion.

## Architecture
- `webapp/` - Flask application (app.py routes, tracker.py data layer, config.py settings)
- `update_tracker.py` - Standalone CLI for quick updates
- `convert_resumes.py` / `convert_coverletters.py` - Document converters
- Data stored in `job_tracker.csv` (not committed; see `job_tracker.example.csv`)

## Configuration
- `webapp/config.py` reads `CANDIDATE_NAME` from environment (default: `Your_Name`)
- File naming pattern: `{CANDIDATE_NAME}_Resume_{Company}.md`
- All personal data (CSV, resumes, cover letters, PDFs) is gitignored

## Development
```bash
source .venv/bin/activate
cd webapp && python3 run.py  # http://localhost:5000
```

## Key Conventions
- CSV field order defined in `tracker.py:FIELDNAMES`
- Status values in `tracker.py:VALID_STATUSES`
- Templates use Jinja2 with `base.html` layout
- Document viewer only serves files under `Resumes/` or `CoverLetters/` (security check in app.py)
- Notes are auto-timestamped when appended via the web UI
