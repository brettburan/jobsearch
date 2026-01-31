#!/usr/bin/env python3
"""Entry point for the Job Search web app."""

from app import app

if __name__ == '__main__':
    print("Job Search Tracker running at http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
