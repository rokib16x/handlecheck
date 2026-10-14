FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[mcp]"
EXPOSE 8000
# default: HTTP API. Override for the CLI or MCP:
#   docker run --rm -i handlecheck handlecheck-mcp
#   docker run --rm handlecheck handlecheck google
CMD ["handlecheck-api", "--host", "0.0.0.0", "--port", "8000"]
