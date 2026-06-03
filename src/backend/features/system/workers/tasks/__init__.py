from src.backend.features.system.workers.tasks.dirty_sweeper import system_dirty_sweeper_task
from src.backend.features.system.workers.tasks.vitals_regen import online_vitals_regen_task

SYSTEM_COORDINATOR_TASKS = (system_dirty_sweeper_task, online_vitals_regen_task)

__all__ = ["SYSTEM_COORDINATOR_TASKS", "system_dirty_sweeper_task", "online_vitals_regen_task"]
