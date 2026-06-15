FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl docker-cli \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) COMPOSE_ARCH=x86_64 ;; \
         arm64) COMPOSE_ARCH=aarch64 ;; \
         *) COMPOSE_ARCH="$ARCH" ;; \
       esac \
    && mkdir -p /usr/local/lib/docker/cli-plugins \
    && curl -fsSL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-${COMPOSE_ARCH}" \
       -o /usr/local/lib/docker/cli-plugins/docker-compose \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose \
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
