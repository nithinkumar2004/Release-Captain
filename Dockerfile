FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY server ./server
RUN python -m pip install --no-cache-dir . && useradd --create-home --uid 10001 recap \
    && chown -R recap:recap /app
USER recap

ENV PYTHONPATH=/app
EXPOSE 8765
CMD ["python", "-m", "server.hosted_ai.app"]
