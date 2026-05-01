FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    BUN_INSTALL=/root/.bun \
    PATH="/root/.bun/bin:/root/.local/bin:${PATH}" \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        curl \
        git \
        lsof \
        nodejs \
        npm \
        psmisc \
        procps \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://bun.sh/install | bash \
    && npm install -g opencode-ai@latest \
    && opencode --version \
    && bun --version \
    && uv --version \
    && chromium --version

WORKDIR /workspace

RUN bun create vite my-app --template vanilla --no-interactive \
    && cd my-app \
    && bun install

COPY opencode.json /workspace/my-app/opencode.json
COPY demoEnvironment/server-communication /workspace/server-communication

WORKDIR /workspace/my-app

CMD ["bun", "dev", "--host", "0.0.0.0"]
