#!/usr/bin/env bash
# Build script for Render deployment

# Exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input
