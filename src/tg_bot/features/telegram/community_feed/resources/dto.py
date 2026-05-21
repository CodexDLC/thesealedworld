from pydantic import BaseModel


class CommunityFeedPayload(BaseModel):
    """DTO for passing data within the CommunityFeed feature."""

    id: int
    # Add your fields here
