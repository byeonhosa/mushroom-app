FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# requirements.txt is a hashed lockfile (see requirements.in).
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY backend /app

# The API needs no write access to its own files; run it unprivileged.
RUN useradd --system --uid 10001 --no-create-home app
USER app

EXPOSE 8000

# --proxy-headers: the client's address and scheme arrive in X-Forwarded-*
# headers from the proxy (Caddy, or the frontend's own /api forwarder). They
# are trusted from any peer because the only peers are the other containers
# and the server's loopback interface: the port is not published elsewhere.
CMD ["sh", "-c", "python -m app.migrate && python -m app.seed_species && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
