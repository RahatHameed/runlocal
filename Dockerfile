FROM python:3.12-slim

LABEL maintainer="Rahat Hameed"
LABEL description="Lightweight framework for running local automation scripts"

WORKDIR /app

# Install gh CLI (required for workflow-dispatch script)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command (use absolute path since working_dir may be /workspace)
ENTRYPOINT ["python", "/app/run.py"]
