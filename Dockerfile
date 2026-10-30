# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Joe King AI-Native Portfolio
# Single-stage Python 3.11 slim container.
# Serves both the FastAPI backend and the static frontend on port 8000.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent .pyc files and enable immediate log output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default port — can be overridden by Hamravesh env var at runtime
ENV PORT=8000

WORKDIR /app

# Install dependencies first (layer-cached when only code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/   ./backend/
COPY data/      ./data/
COPY frontend/  ./frontend/

# Expose the port
EXPOSE 8000

# Run with uvicorn — PORT env var allows Hamravesh to override at runtime
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
