FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv pip install --frozen --no-cache --python /usr/local/bin/python3 .
CMD ["python", "-m", "yacloud_watcher"]
