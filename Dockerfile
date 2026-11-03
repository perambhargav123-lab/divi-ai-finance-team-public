# Divi demo image. Public build is replay only: answers recorded from real Muse runs, no model keys.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY divi divi
COPY data data
COPY out out
COPY scripts scripts
ENV PORT=8000 DIVI_MOCK=1 DIVI_LIVE=0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn divi.app:app --host 0.0.0.0 --port ${PORT}"]
