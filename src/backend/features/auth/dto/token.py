from pydantic import BaseModel

from src.backend.core.schemas.base import BaseRequest, BaseResponse


class Token(BaseResponse):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None


class RefreshTokenRequest(BaseRequest):
    refresh_token: str
