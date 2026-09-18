FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY app ./app
RUN pip install --no-cache-dir --require-hashes -r requirements.txt && pip install --no-cache-dir --no-deps . && useradd --create-home appuser
USER appuser
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
