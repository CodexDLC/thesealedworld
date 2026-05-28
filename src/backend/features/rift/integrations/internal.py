from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.rift.services.dev_service import RiftDevService

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftScreenDTO, RiftStartRequestDTO
    from src.backend.features.rift.integrations.runtime import RiftRuntimeIntegration


async def create_dev_rift_screen(
    runtime: RiftRuntimeIntegration,
    request: RiftStartRequestDTO,
) -> RiftScreenDTO:
    return await RiftDevService(runtime=runtime).start(request)


async def get_dev_rift_screen(runtime: RiftRuntimeIntegration, rift_instance_id: str) -> RiftScreenDTO:
    return await RiftDevService(runtime=runtime).screen(rift_instance_id)
