FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY packages/upskill_content packages/upskill_content
COPY apps/sandbox-worker apps/sandbox-worker
RUN pip install ./packages/upskill_content ./apps/sandbox-worker
# worker работает от root только ради доступа к Docker socket; пользовательский код выполняется
# исключительно внутри ограниченных контейнеров-песочниц, а не в этом процессе
ENV CONTENT_DIR=/app/content
WORKDIR /app/apps/sandbox-worker
EXPOSE 8100
CMD ["python", "-m", "worker.main"]
