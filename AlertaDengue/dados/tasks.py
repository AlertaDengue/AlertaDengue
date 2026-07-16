from datetime import datetime
from typing import Literal

from celery.schedules import crontab
from episcanner.scanner import EpiScanner
import pandas as pd
from sqlalchemy import text

from ad_main.celeryapp import app
from dados.dbdata import (
    ALL_STATE_NAMES,
    CID10,
    DB_ENGINE,
    get_disease_suffix,
)


def _normalize_disease(disease: str) -> str:
    return "chikungunya" if disease == "chik" else disease


app.conf.beat_schedule = {
    "episcanner-dengue-current-year": {
        "task": "dados.tasks.episcanner_all_states",
        "schedule": crontab(minute=0, hour=3, day_of_week=1),
        "args": (datetime.now().year, "dengue"),
    },
    "episcanner-zika-current-year": {
        "task": "dados.tasks.episcanner_all_states",
        "schedule": crontab(minute=0, hour=3, day_of_week=2),
        "args": (datetime.now().year, "zika"),
    },
    "episcanner-chik-current-year": {
        "task": "dados.tasks.episcanner_all_states",
        "schedule": crontab(minute=0, hour=3, day_of_week=3),
        "args": (datetime.now().year, "chik"),
    },
}


def _fetch_alert_data(
    state_abbr: str, disease: str, year: int
) -> pd.DataFrame:
    long_name = _normalize_disease(disease)
    suffix = get_disease_suffix(long_name)
    state_name = ALL_STATE_NAMES[state_abbr][0]
    se_start = year * 100 + 1
    se_end = year * 100 + 53

    sql = f"""
    SELECT
        h."data_iniSE",
        h."SE",
        h.casos_est,
        h.municipio_geocodigo,
        h.p_rt1
    FROM "Municipio"."Historico_alerta{suffix}" AS h
    JOIN "Dengue_global"."Municipio" AS m
        ON h.municipio_geocodigo = m.geocodigo
    WHERE m.uf = :state_name
        AND h."SE" >= :se_start
        AND h."SE" <= :se_end
    ORDER BY h."SE"
    """

    with DB_ENGINE.connect() as conn:
        result = conn.execute(
            text(sql),
            {
                "state_name": state_name,
                "se_start": se_start,
                "se_end": se_end,
            },
        )
        return pd.DataFrame(result.fetchall(), columns=list(result.keys()))


def _save_sir_params(disease: str, year: int, results: list) -> int:
    from dados.models import EpiscannerSirParams

    long_name = _normalize_disease(disease)
    cid10 = CID10[long_name]
    saved = 0

    for r in results:
        EpiscannerSirParams.objects.update_or_create(
            cid10=cid10,
            geocode_id=r.geocode,
            year=year,
            defaults={
                "ep_ini": r.ep_ini,
                "ep_pw": r.ep_pw,
                "ep_end": r.ep_end,
                "ep_dur": r.ep_dur,
                "peak_week": r.peak_week,
                "beta": r.beta,
                "gamma": r.gamma,
                "r0": r.R0,
                "total_cases": r.total_cases,
                "alpha": r.alpha,
                "sum_res": r.sum_res,
                "t_ini": r.t_ini,
                "t_end": r.t_end,
            },
        )
        saved += 1

    return saved


@app.task
def episcanner_scan_state(
    state_abbr: str,
    disease: Literal["dengue", "zika", "chik"],
    year: int,
):
    df = _fetch_alert_data(state_abbr, disease, year)
    if df.empty:
        return f"{state_abbr}/{disease}/{year}: no data"

    scanner = EpiScanner(df, year)
    results = scanner.richards()
    saved = _save_sir_params(disease, year, results)

    return f"{state_abbr}/{disease}/{year}: {saved} cities saved"


@app.task
def episcanner_all_states(
    year: int,
    disease: Literal["dengue", "zika", "chik"],
):
    for state_abbr in ALL_STATE_NAMES:
        episcanner_scan_state.delay(state_abbr, disease, year)
