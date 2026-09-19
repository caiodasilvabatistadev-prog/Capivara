FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --require-hashes -r requirements.txt \
    && pip install --no-cache-dir --no-deps . \
    && useradd --create-home appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data \
    && chmod 755 /usr/local/bin/docker-entrypoint.sh
ENV PORT=8000
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
