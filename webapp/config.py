"""
Configuration for the Job Search Tracker.

Settings can be overridden via environment variables or a .env file.
"""

import os

# Candidate name used for resume/cover letter file naming.
# Format: "FirstName_LastName" (underscores, no spaces).
# Controls file patterns like: {CANDIDATE_NAME}_Resume_{Company}.md
CANDIDATE_NAME = os.environ.get('CANDIDATE_NAME', 'Your_Name')

# Filename prefix derived from candidate name
RESUME_PREFIX = f'{CANDIDATE_NAME}_Resume_'
COVER_LETTER_PREFIX = f'{CANDIDATE_NAME}_CoverLetter_'

# Base resume filename (the original/master resume)
BASE_RESUME_FILENAME = os.environ.get(
    'BASE_RESUME_FILENAME',
    f'{CANDIDATE_NAME}_Resume.pdf',
)
