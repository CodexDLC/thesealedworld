from src.backend.features.system.workers.tasks.dirty_sweeper import system_dirty_sweeper_task

SYSTEM_COORDINATOR_TASKS = (system_dirty_sweeper_task,)

__all__ = ["SYSTEM_COORDINATOR_TASKS", "system_dirty_sweeper_task"]
