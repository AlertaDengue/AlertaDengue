from datetime import datetime

from celery.schedules import crontab
from scanner.scanner import EpiScanner

from django.conf import settings
from ad_main.celeryapp import app
from dados.dbdata import ALL_STATE_NAMES

app.conf.beat_schedule = {
    "episcanner-dengue-current-year": {
        "task": "dados.tasks.episcanner_dengue_cur_year",
        "schedule": crontab(minute=0, hour=3, day_of_month=13),
    },
    "episcanner-zika-current-year": {
        "task": "dados.tasks.episcanner_zika_cur_year",
        "schedule": crontab(minute=0, hour=3, day_of_month=14),
    },
    "episcanner-chik-current-year": {
        "task": "dados.tasks.episcanner_chik_cur_year",
        "schedule": crontab(minute=0, hour=3, day_of_month=15),
    },
}

CUR_YEAR = datetime.now().year


@app.task
def episcanner_dengue_cur_year():
    """
    Runs EpiScanner for all states for dengue in the current year and exports
    to MEDIA ROOT in the duckdb format
    """
    for state in ALL_STATE_NAMES:
        scanner = EpiScanner(
            disease="dengue",
            uf=state,
            year=CUR_YEAR
        )
        scanner.export("duckdb", output_dir=settings.MEDIA_ROOT)


@app.task
def episcanner_zika_cur_year():
    """
    Runs EpiScanner for all states for zika in the current year and exports
    to MEDIA ROOT in the duckdb format
    """
    for state in ALL_STATE_NAMES:
        scanner = EpiScanner(
            disease="zika",
            uf=state,
            year=CUR_YEAR
        )
        scanner.export("duckdb", output_dir=settings.MEDIA_ROOT)


@app.task
def episcanner_chik_cur_year():
    """
    Runs EpiScanner for all states for chikungunya in the current year and 
    exports to MEDIA ROOT in the duckdb format
    """
    for state in ALL_STATE_NAMES:
        scanner = EpiScanner(
            disease="chik",
            uf=state,
            year=CUR_YEAR
        )
        scanner.export("duckdb", output_dir=settings.MEDIA_ROOT)
