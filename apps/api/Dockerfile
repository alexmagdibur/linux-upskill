FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY packages/upskill_content packages/upskill_content
COPY apps/api apps/api
RUN pip install ./packages/upskill_content ./apps/api && useradd -r -u 10001 api
# контент (манифесты и публичные данные) нужен только seed-команде; сами скрипты проверок API не исполняет
COPY content /app/content
ENV CONTENT_DIR=/app/content
USER api
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
