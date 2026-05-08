from src.backend.features.inventory.workers.tasks.session_tasks import (
    flush_inventory_session_task,
    inventory_dirty_sweeper_task,
)

INVENTORY_TASKS = (flush_inventory_session_task, inventory_dirty_sweeper_task)

__all__ = ["INVENTORY_TASKS", "flush_inventory_session_task", "inventory_dirty_sweeper_task"]
