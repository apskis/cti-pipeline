# CTI pipeline — ONE image for all Claude Code components.
# COMPONENT selects which components/<name>/task.md to run.
# CLOUD (aws|azure) selects where output is shipped. Model is Claude on Bedrock in both.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates git unzip gnupg build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Node 20 + Claude Code CLI (agent runtime)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

# uv for the threatpipe MCP servers
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# AWS CLI v2 (Bedrock preflight + S3 output)
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp && /tmp/aws/install && rm -rf /tmp/aws*
# Azure CLI — the same image ships both CLIs so CLOUD=aws|azure both work.
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN chmod +x deploy/entrypoint.sh && (uv sync --frozen 2>/dev/null || uv sync || true)

# Model backend defaults to Bedrock; entrypoint sets CLAUDE_CODE_USE_BEDROCK when
# MODEL_BACKEND=bedrock, or reads CLAUDE_CODE_OAUTH_TOKEN when =subscription.
ENV MODEL_BACKEND=bedrock \
    THREATPIPE_ROOT=/app/core/threatpipe \
    OUTPUT_DIR=/app/out
ENTRYPOINT ["deploy/entrypoint.sh"]
