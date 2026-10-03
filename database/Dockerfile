# ── Database Migrations Runner ──────────────────────────────
# Runs Alembic migrations then exits.
# Used as a one-shot container in docker-compose.
# ────────────────────────────────────────────────────────────

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    alembic==1.14.1 \
    sqlalchemy==2.0.36 \
    psycopg2-binary==2.9.10

# Copy database module and migrations
COPY database/ ./database/

# Run migrations
CMD ["alembic", "-c", "database/alembic.ini", "upgrade", "head"]
