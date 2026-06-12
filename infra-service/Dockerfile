FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends docker-cli \
    && rm -rf /var/lib/apt/lists/*

COPY infra-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY infra-service/src ./src
COPY stacks /stacks
COPY catalog /catalog

ENV STACKS_PATH=/stacks
ENV INSTANCES_DATA_PATH=/app/data/instances
ENV PYTHONPATH=/app

EXPOSE 9000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9000"]
