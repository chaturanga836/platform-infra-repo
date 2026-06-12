from fastapi import Header, HTTPException

from src.config import settings


def verify_internal_token(x_internal_token: str = Header(..., alias="X-Internal-Token")) -> None:
    if x_internal_token != settings.INTERNAL_SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid internal service token")
