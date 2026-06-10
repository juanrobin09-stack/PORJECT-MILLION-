FROM python:3.11-slim

WORKDIR /srv/sona

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY sona ./sona
RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8000

# API by default; the worker runs as a second container with:
#   command: python -m sona.worker
CMD ["uvicorn", "sona.main:app", "--host", "0.0.0.0", "--port", "8000"]
