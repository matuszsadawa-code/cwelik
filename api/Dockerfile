# ============================================================
# Stage 1: Builder — install dependencies
# ============================================================
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build tools needed for some packages (e.g. bcrypt, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for layer caching
COPY requirements.txt .

# Install into a prefix so we can copy cleanly to the final stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ============================================================
# Stage 2: Production image
# ============================================================
FROM python:3.10-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create directory for the SQLite database (volume mount point)
RUN mkdir -p /app/db

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Use server:app as the entry point (legacy-compatible)
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
