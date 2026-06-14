FROM python:3.13.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build wheels in a builder stage to avoid compiling in the final image
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && pip wheel -r requirements.txt -w /wheels

FROM python:3.13.12-slim

# Runtime deps only; keep image small
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages from the prebuilt wheelhouse
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt

# Copy application code
COPY . /app

# Create an unprivileged user and take ownership of the app directory
RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run as non-root user
USER app

EXPOSE 8000

CMD ["sh", "-c", "PYTHONPATH=/app/viable_graph_project python viable_graph_project/manage.py collectstatic --noinput && PYTHONPATH=/app/viable_graph_project gunicorn viable_graph_project.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-1}"]
