FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install uv for fast dependency resolution and installation
RUN pip install uv

COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY . .

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
