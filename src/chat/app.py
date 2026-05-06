from fastapi import FastAPI

from src.chat.api.router import router as chat_rest_router
from src.chat.api.ws import router as chat_ws_router
from src.chat.core.lifespan import lifespan

app = FastAPI(title="TurnBasedMMORPG Chat Service", lifespan=lifespan)

app.include_router(chat_ws_router)
app.include_router(chat_rest_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
