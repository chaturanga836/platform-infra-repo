from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "BaaS Infra Service"
    DEBUG: bool = False
    INTERNAL_SERVICE_TOKEN: str = "changeme-internal-token"

    # docker | local — local uses LOCAL_POSTGRES_URL for dev without per-project containers
    PROVISION_MODE: str = "local"

    DATA_PLANE_NETWORK: str = "data-plane-net"
    STACKS_PATH: Path = _ROOT / "stacks"
    INSTANCES_DATA_PATH: Path = _ROOT / "data" / "instances"

    # Used when PROVISION_MODE=local (shared postgres for demo/dev)
    LOCAL_POSTGRES_URL: str = "postgresql://elt:changeme@localhost:5432/postgres"

    POSTGRES_IMAGE: str = "postgres:16-alpine"
    POSTGRES_USER: str = "baas"
    # Bootstrap catalog for dedicated project containers only; shared Studio
    # schemas use LOCAL_POSTGRES_URL (typically dtorc_workspace).
    POSTGRES_DB: str = "dtorc_workspace"

    REDIS_IMAGE: str = "redis:7.2-alpine"
    LOCAL_REDIS_URL: str = "redis://redis:6379/1"

    CENTRIFUGO_IMAGE: str = "centrifugo/centrifugo:v5"

    MINIO_IMAGE: str = "minio/minio:RELEASE.2024-12-18T13-15-44Z"
    SHARED_MINIO_BUCKET: str = "crypto-lake"
    DEDICATED_MINIO_BUCKET: str = "data"
    LOCAL_MINIO_ENDPOINT: str = "http://localhost:9000"
    LOCAL_MINIO_ACCESS_KEY: str = "minioadmin"
    LOCAL_MINIO_SECRET_KEY: str = "minioadmin"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
