FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY extract_geoparquet_layer.py run_extract_geoparquet.py ./

ENTRYPOINT ["uv", "run", "--no-sync", "python", "run_extract_geoparquet.py"]