from ad_main.celeryapp import app
from celery.schedules import crontab

from loguru import logger

app.conf.beat_schedule = {
    "hi": {
        "task": "dados.tasks.say_hi",
        "schedule": crontab(minute=1),
    },
}


@app.task
def say_hi():
    logger.warning("hi")
