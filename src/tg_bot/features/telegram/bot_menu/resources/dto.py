from pydantic import BaseModel


class MenuPayload(BaseModel):
    """Payload for menu navigation."""

    action: str
    target: str | None = None
