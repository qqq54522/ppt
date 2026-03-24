import logging
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
from models import db
from models.task import Task

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def get_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def submit_task(app: Flask, task_id: str, fn, *args, **kwargs):
    executor = get_executor(app.config.get("MAX_IMAGE_WORKERS", 4))

    def _wrapper():
        with app.app_context():
            try:
                _update_task(task_id, status="running")
                fn(task_id, *args, **kwargs)
                _update_task(task_id, status="completed", progress=100.0)
            except Exception as e:
                logger.exception("Task %s failed: %s", task_id, e)
                _update_task(task_id, status="failed", error=str(e))

    executor.submit(_wrapper)


def _update_task(task_id: str, **fields):
    task = db.session.get(Task, task_id)
    if task:
        for k, v in fields.items():
            setattr(task, k, v)
        db.session.commit()


def update_task_progress(task_id: str, progress: float, result=None):
    fields = {"progress": progress}
    if result is not None:
        fields["result"] = result
    _update_task(task_id, **fields)
