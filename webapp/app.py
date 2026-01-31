"""
Flask web application for the Job Search tracker.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from pathlib import Path
import markdown2

from config import BASE_RESUME_FILENAME
from tracker import (
    load_jobs, add_job, update_job, delete_job, get_job,
    hide_job, unhide_job,
    compute_stats, get_followups, list_documents, read_markdown,
    get_company_documents,
    VALID_STATUSES, INTERVIEW_STAGES, FIELDNAMES, PRIORITY_ORDER,
    RESUMES_DIR, COVERLETTERS_DIR,
)

app = Flask(__name__)
app.secret_key = 'jobsearch-local-dev-key'


@app.route('/')
def dashboard():
    stats = compute_stats()
    followups = get_followups()
    return render_template('dashboard.html', stats=stats, followups=followups)


@app.route('/jobs')
def jobs_list():
    jobs = load_jobs()
    # Attach original index for linking
    for i, job in enumerate(jobs):
        job['_index'] = i

    # Filters
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    show_hidden = request.args.get('show_hidden', '')
    group_filter = request.args.get('group', '')
    if not show_hidden:
        jobs = [j for j in jobs if j.get('Hidden', '').lower() != 'yes']
    if group_filter == 'applied':
        jobs = [j for j in jobs if j.get('Status') != 'Not Applied']
    elif group_filter == 'not_applied':
        jobs = [j for j in jobs if j.get('Status') == 'Not Applied']
    elif group_filter == 'interviewing':
        jobs = [j for j in jobs if 'Interview' in j.get('Status', '') or 'Screen' in j.get('Status', '')]
    elif group_filter == 'offers':
        jobs = [j for j in jobs if 'Offer' in j.get('Status', '')]
    elif group_filter == 'rejected':
        jobs = [j for j in jobs if j.get('Status') in ('Rejected', 'No Response', 'Position Closed')]
    if status_filter:
        jobs = [j for j in jobs if j.get('Status') == status_filter]
    if priority_filter:
        jobs = [j for j in jobs if j.get('Priority') == priority_filter]

    # Sorting
    sort_by = request.args.get('sort', '')
    sort_dir = request.args.get('dir', 'asc')
    if sort_by:
        reverse = sort_dir == 'desc'
        if sort_by == 'priority':
            jobs.sort(key=lambda j: PRIORITY_ORDER.get(j.get('Priority', 'Medium'), 2), reverse=reverse)
        elif sort_by == 'company':
            jobs.sort(key=lambda j: j.get('Company', '').lower(), reverse=reverse)
        elif sort_by == 'status':
            jobs.sort(key=lambda j: j.get('Status', ''), reverse=reverse)
        elif sort_by == 'salary':
            jobs.sort(key=lambda j: j.get('Total Comp Est.', ''), reverse=reverse)

    # Collect unique statuses/priorities for filter dropdowns
    all_jobs = load_jobs()
    statuses = sorted(set(j.get('Status', '') for j in all_jobs if j.get('Status')))
    priorities = ['Critical', 'High', 'Medium', 'Low']

    group_labels = {
        'applied': 'Applied', 'not_applied': 'Not Applied',
        'interviewing': 'Interviewing', 'offers': 'Offers', 'rejected': 'Rejected/Closed',
    }
    return render_template('jobs.html', jobs=jobs, statuses=statuses, priorities=priorities,
                           status_filter=status_filter, priority_filter=priority_filter,
                           sort_by=sort_by, sort_dir=sort_dir, show_hidden=show_hidden,
                           group_filter=group_filter, group_label=group_labels.get(group_filter, ''))


@app.route('/jobs/new', methods=['GET', 'POST'])
def job_new():
    if request.method == 'POST':
        data = {field: request.form.get(field, '') for field in FIELDNAMES}
        job = add_job(data)
        flash(f"Added: {job['Company']} - {job['Position']}", 'success')
        return redirect(url_for('jobs_list'))
    return render_template('job_form.html', job=None, index=None,
                           statuses=VALID_STATUSES, stages=INTERVIEW_STAGES)


@app.route('/jobs/<int:index>')
def job_detail(index):
    job, idx = get_job(index)
    if job is None:
        abort(404)
    company_docs = get_company_documents(job.get('Company', ''))
    return render_template('job_detail.html', job=job, index=idx, company_docs=company_docs)


@app.route('/jobs/<int:index>/edit', methods=['GET', 'POST'])
def job_edit(index):
    if request.method == 'POST':
        data = {field: request.form.get(field, '') for field in FIELDNAMES}
        # Notes field: only pass if user typed something new
        notes_append = request.form.get('notes_append', '').strip()
        notes_replace = request.form.get('notes_replace', '')
        if notes_append:
            data['Notes'] = notes_append
        else:
            # Direct replacement of entire notes field
            data.pop('Notes', None)
            if notes_replace is not None:
                jobs = load_jobs()
                if 0 <= index < len(jobs):
                    jobs[index]['Notes'] = notes_replace
                    for field in FIELDNAMES:
                        if field != 'Notes' and field in data:
                            jobs[index][field] = data[field].strip()
                    # Auto follow-up
                    if data.get('Applied Date') and not jobs[index].get('Next Follow-Up'):
                        try:
                            from datetime import datetime, timedelta
                            d = datetime.strptime(jobs[index]['Applied Date'], '%Y-%m-%d')
                            jobs[index]['Next Follow-Up'] = (d + timedelta(days=7)).strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    if jobs[index]['Applied Date'] and jobs[index]['Status'] == 'Not Applied':
                        jobs[index]['Status'] = 'Applied'
                    from tracker import save_jobs
                    save_jobs(jobs)
                    flash(f"Updated: {jobs[index]['Company']} - {jobs[index]['Position']}", 'success')
                    return redirect(url_for('job_detail', index=index))

        updated = update_job(index, data)
        if updated:
            flash(f"Updated: {updated['Company']} - {updated['Position']}", 'success')
        else:
            flash("Job not found.", 'error')
        return redirect(url_for('job_detail', index=index))

    job, idx = get_job(index)
    if job is None:
        abort(404)
    return render_template('job_form.html', job=job, index=idx,
                           statuses=VALID_STATUSES, stages=INTERVIEW_STAGES)


@app.route('/jobs/<int:index>/delete', methods=['POST'])
def job_delete(index):
    job, _ = get_job(index)
    if job:
        company = job['Company']
        position = job['Position']
        delete_job(index)
        flash(f"Deleted: {company} - {position}", 'success')
    else:
        flash("Job not found.", 'error')
    return redirect(url_for('jobs_list'))


@app.route('/jobs/<int:index>/hide', methods=['POST'])
def job_hide(index):
    job, _ = get_job(index)
    if job:
        hide_job(index)
        flash(f"Hidden: {job['Company']} - {job['Position']}", 'success')
    else:
        flash("Job not found.", 'error')
    return redirect(url_for('jobs_list'))


@app.route('/jobs/<int:index>/unhide', methods=['POST'])
def job_unhide(index):
    job, _ = get_job(index)
    if job:
        unhide_job(index)
        flash(f"Restored: {job['Company']} - {job['Position']}", 'success')
    else:
        flash("Job not found.", 'error')
    return redirect(url_for('job_detail', index=index))


@app.route('/base-resume')
def base_resume():
    base_pdf = Path(app.root_path).parent / BASE_RESUME_FILENAME
    if not base_pdf.exists():
        abort(404)
    return send_file(base_pdf.resolve(), as_attachment=False)


@app.route('/documents')
def documents():
    docs = list_documents()
    return render_template('documents.html', docs=docs)


@app.route('/documents/view')
def document_view():
    filepath = request.args.get('path', '')
    if not filepath:
        abort(400)
    # Security: only allow files under Resumes/ or CoverLetters/
    p = Path(filepath).resolve()
    if not (str(p).startswith(str(RESUMES_DIR.resolve())) or
            str(p).startswith(str(COVERLETTERS_DIR.resolve()))):
        abort(403)
    content = read_markdown(filepath)
    if content is None:
        abort(404)
    html_content = markdown2.markdown(content, extras=['tables', 'fenced-code-blocks'])
    filename = Path(filepath).stem
    return render_template('document_view.html', content=html_content, filename=filename)


@app.route('/documents/download/<path:filename>')
def document_download(filename):
    # Check both Resumes and CoverLetters directories
    for directory in [RESUMES_DIR, COVERLETTERS_DIR]:
        filepath = directory / filename
        if filepath.exists() and filepath.suffix in ('.pdf', '.docx'):
            resolved = filepath.resolve()
            if str(resolved).startswith(str(directory.resolve())):
                return send_file(resolved, as_attachment=True)
    abort(404)
