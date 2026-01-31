#!/usr/bin/env python3
"""Convert cover letter markdown files to PDF (default) or DOCX."""
import sys
import argparse
sys.path.insert(0, '.')
from convert_resumes import md_to_docx, md_to_cover_letter_pdf
from pathlib import Path

parser = argparse.ArgumentParser(description='Convert cover letters')
parser.add_argument('--pdf', action='store_true', default=True, help='Convert to PDF (default)')
parser.add_argument('--docx', action='store_true', help='Convert to DOCX instead of PDF')
args = parser.parse_args()

fmt = 'docx' if args.docx else 'pdf'
ext = f'.{fmt}'
converter = md_to_docx if args.docx else md_to_cover_letter_pdf

base_dir = Path(__file__).parent
cl_dir = base_dir / 'CoverLetters'

md_files = sorted(cl_dir.glob('*.md'))
print(f"Converting {len(md_files)} cover letters to {fmt.upper()}...\n")
for md_file in md_files:
    out_name = md_file.stem + ext
    output_path = cl_dir / out_name
    try:
        converter(str(md_file), str(output_path))
        print(f"  ✓ {md_file.name} → {out_name}")
    except Exception as e:
        print(f"  ✗ {md_file.name} FAILED: {e}")

print(f"\nDone! Cover letters converted to {cl_dir}/")
