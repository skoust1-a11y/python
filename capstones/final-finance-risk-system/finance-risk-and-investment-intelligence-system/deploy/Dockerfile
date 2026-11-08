# FastAPI API image. UI ships on Vercel; DB stays external.
FROM python:3.11-slim
WORKDIR /app
RUN useradd -r -u 10001 appuser
COPY capstone/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY capstone/ ./
RUN mkdir -p /app/logs && chown -R appuser /app/logs
USER appuser
ENV APP_ENV=prod APP_HOST=0.0.0.0 APP_PORT=8000 PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
