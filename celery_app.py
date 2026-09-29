import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv() # used to load my env variables from .env

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
 
celery_app = Celery(
    "email_alerting",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks", "pipeline"],  # tells the worker to import both and register their tasks
)
 
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
 

# Automatic trigger: runs the alert pipeline every 10 seconds without
# anyone manually running main.py. 
# Needs `celery -A celery_app beat`  # running alongside the worker.

celery_app.conf.beat_schedule = {
    "run-alert-pipeline": {
        "task": "pipeline.run_pipeline_task",
        "schedule": 10.0, # interval
    },
}