# backend/router.py
from fastapi import APIRouter

from src.backend.domains.user_features.combat.api.router import router as combat_router
from src.backend.domains.user_features.inventory.api.router import router as inventory_router

api_router = APIRouter()

# Описание тегов для Swagger
tags_metadata = [
    {
        "name": "System",
        "description": "Health check and system info.",
    },
    {
        "name": "Combat",
        "description": "Combat system operations.",
    },
    {
        "name": "Scenario",
        "description": "Quest and dialogue system.",
    },
    {
        "name": "Inventory",
        "description": "Inventory management.",
    },
]

api_router.include_router(combat_router, prefix="/combat", tags=["Combat"])
api_router.include_router(inventory_router, tags=["Inventory"])
