#!/bin/bash
cd /home/fawad/ai/ERP-AI
exec .venv/bin/gunicorn -w 1 --timeout 300 --threads 4 -b 0.0.0.0:5000 'web:app'
