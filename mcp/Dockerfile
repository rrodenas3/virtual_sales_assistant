FROM python:3.11-slim

WORKDIR /app
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/backend /app/backend/backend
COPY mcp /app/mcp
WORKDIR /app/backend
RUN pip install --no-cache-dir -e .
WORKDIR /app

CMD ["python", "-m", "mcp.osa.server", "--list"]
