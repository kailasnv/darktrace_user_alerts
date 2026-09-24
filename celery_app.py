import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv() # used to load my env variables from .env

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
 
celery_app = Celery(
    "email_alerting",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],  # tells the worker to import tasks.py and register its tasks
)
 
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
 

