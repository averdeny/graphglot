# Base image with Python and uv setup
FROM python:3.12-slim AS base

# Set environment variables and working directory
ENV WORKDIR=/graphglot \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR $WORKDIR

# Install uv and other dependencies
RUN pip install --upgrade pip \
    && pip install uv \
    && apt-get update \
    && apt-get install -y make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy relevant config and code
COPY README.md LICENSE pyproject.toml uv.lock Makefile ./
COPY graphglot/ ./graphglot

# Fail fast if uv.lock is out of sync with pyproject.toml
RUN uv lock --check

# Install dependencies into system Python (no venv needed inside Docker)
RUN uv pip install --system -e .

# Test stage
FROM base AS test

# Install additional dependencies for testing
RUN apt-get update && \
    apt-get install -y git procps curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install claude
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
ENV PATH="/root/.local/bin:$PATH"

# Copy test files
COPY tests/ ./tests

# Install development dependencies
RUN uv pip install --system -e .[dev,gen]

# Final image stage
FROM base AS final
