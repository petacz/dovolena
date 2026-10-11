FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m -u 10001 lens && mkdir -p /data && chown -R lens:lens /data /app
USER lens
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,requests; requests.get('http://127.0.0.1:8000/api/health',auth=('lens',os.getenv('APP_PASSWORD','')),timeout=3).raise_for_status()" || exit 1
CMD ["sh", "-c", "python bootstrap.py && exec gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 120 app:app"]
