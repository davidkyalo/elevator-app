FROM ghcr.io/astral-sh/uv:python3.12-alpine

RUN addgroup -S zulu && adduser -S -G zulu zulu

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN chown -R zulu:zulu /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

USER zulu

CMD ["fastapi", "run", "--host", "0.0.0.0", "app/main.py"]
