import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
# Keep defaults tiny for Render free (512MB).
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "1"))
timeout = 120
accesslog = "-"
errorlog = "-"
