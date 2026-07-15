"""Tests for dados.tasks."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

from django.conf import settings
from episcanner.schemas import SirParams
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

TEST_YEAR = 2024
CITIES = {
    "RJ": {
        "name": "Rio de Janeiro",
        "geocodes": [3304557, 3303302],  # Rio de Janeiro, Niterói
    },
    "SP": {
        "name": "São Paulo",
        "geocodes": [3550308, 3509502],  # São Paulo, Campinas
    },
}


@pytest.fixture()
def db_engine() -> Engine:
    return getattr(settings, "DB_ENGINE")


@pytest.fixture()
def episcanner_data_tables(db_engine: Engine) -> Iterator[None]:
    all_geocodes = [gc for uf in CITIES.values() for gc in uf["geocodes"]]

    with db_engine.begin() as conn:
        conn.execute(text('CREATE SCHEMA IF NOT EXISTS "Municipio"'))

        for suffix in ["", "_chik", "_zika"]:
            table_name = f"Historico_alerta{suffix}"
            conn.execute(
                text(
                    f'DROP TABLE IF EXISTS "Municipio"."{table_name}" CASCADE'
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE "Municipio"."{table_name}" (
                        id SERIAL PRIMARY KEY,
                        "SE" INTEGER,
                        "data_iniSE" DATE,
                        municipio_geocodigo BIGINT,
                        casos_est REAL,
                        p_rt1 REAL
                    )
                    """
                )
            )

        def _insert_data(suffix: str, gc: int, base_cases: float) -> None:
            table = f'"Municipio"."Historico_alerta{suffix}"'
            values = ",\n".join(
                f"  ({TEST_YEAR * 100 + w:06d}, "
                f"'{TEST_YEAR}-{m:02d}-{d:02d}'::date, "
                f"{gc}, {base_cases * w:.1f}, {0.5 + w * 0.05:.2f})"
                for w, (m, d) in enumerate(
                    [
                        (1, 1),
                        (1, 8),
                        (1, 15),
                        (1, 22),
                        (1, 29),
                        (2, 5),
                        (2, 12),
                        (2, 19),
                        (2, 26),
                        (3, 4),
                    ],
                    start=1,
                )
            )
            conn.execute(
                text(
                    f"INSERT INTO {table} "
                    '("SE", "data_iniSE", municipio_geocodigo, casos_est, p_rt1) '
                    f"VALUES\n{values}"
                )
            )

        for gc in all_geocodes:
            base = 30.0 if gc < 3500000 else 60.0
            _insert_data("", gc, base)
            _insert_data("_chik", gc, base * 0.5)
            _insert_data("_zika", gc, base * 0.3)

        conn.execute(
            text(
                'ALTER TABLE "Dengue_global"."Municipio" '
                "ADD COLUMN IF NOT EXISTS nome TEXT, "
                "ADD COLUMN IF NOT EXISTS uf TEXT"
            )
        )
        for uf_abbr, info in CITIES.items():
            for gc in info["geocodes"]:
                conn.execute(
                    text(
                        'INSERT INTO "Dengue_global"."Municipio" '
                        "(geocodigo, nome, uf) "
                        "VALUES (:gc, :name, :uf) "
                        "ON CONFLICT (geocodigo) "
                        "DO UPDATE SET nome = EXCLUDED.nome, uf = EXCLUDED.uf"
                    ),
                    {"gc": gc, "name": info["name"], "uf": info["name"]},
                )

    yield

    with db_engine.begin() as conn:
        conn.execute(text('DROP SCHEMA IF EXISTS "Municipio" CASCADE'))
        for uf_info in CITIES.values():
            for gc in uf_info["geocodes"]:
                try:
                    conn.execute(
                        text(
                            'DELETE FROM "Dengue_global"."Municipio" '
                            "WHERE geocodigo = :gc"
                        ),
                        {"gc": gc},
                    )
                except Exception:
                    pass


@pytest.fixture()
def mock_sir_params() -> list[SirParams]:
    results = []
    for gc in [3304557, 3303302, 3550308, 3509502]:
        results.append(
            SirParams(
                geocode=gc,
                year=TEST_YEAR,
                ep_ini=f"{TEST_YEAR}05",
                ep_pw=f"{TEST_YEAR}10",
                ep_end=f"{TEST_YEAR}16",
                ep_dur=12,
                peak_week=10.0 + (gc % 10),
                beta=1.5 + (gc % 3) * 0.1,
                gamma=0.5,
                R0=2.0 + (gc % 5) * 0.5,
                total_cases=1000.0 + (gc % 1000),
                alpha=0.95,
                sum_res=50.0 + (gc % 100),
                t_ini=5,
                t_end=16 + (gc % 3),
            )
        )
    return results


@pytest.fixture()
def sir_params_table() -> Iterator[None]:
    from django.db import connections

    from dados.models import EpiscannerSirParams

    all_geocodes = [gc for uf in CITIES.values() for gc in uf["geocodes"]]
    with connections["dados"].cursor() as cur:
        for gc in all_geocodes:
            cur.execute(
                'INSERT INTO "Dengue_global"."Municipio" (geocodigo) '
                "VALUES (%s) ON CONFLICT (geocodigo) DO NOTHING",
                [gc],
            )

    with connections["dados"].schema_editor() as editor:
        editor.create_model(EpiscannerSirParams)
    yield
    with connections["dados"].schema_editor() as editor:
        editor.delete_model(EpiscannerSirParams)
    with connections["dados"].cursor() as cur:
        for gc in all_geocodes:
            cur.execute(
                'DELETE FROM "Dengue_global"."Municipio" WHERE geocodigo = %s',
                [gc],
            )


class TestFetchAlertData:
    @pytest.mark.django_db(transaction=True)
    def test_returns_expected_columns(
        self, episcanner_data_tables: None
    ) -> None:
        from dados.tasks import _fetch_alert_data

        df = _fetch_alert_data("RJ", "dengue", TEST_YEAR)

        assert set(df.columns) == {
            "data_iniSE",
            "SE",
            "casos_est",
            "municipio_geocodigo",
            "p_rt1",
        }

    @pytest.mark.django_db(transaction=True)
    def test_filters_by_state(self, episcanner_data_tables: None) -> None:
        from dados.tasks import _fetch_alert_data

        df_rj = _fetch_alert_data("RJ", "dengue", TEST_YEAR)
        df_sp = _fetch_alert_data("SP", "dengue", TEST_YEAR)

        rj_codes = set(CITIES["RJ"]["geocodes"])
        sp_codes = set(CITIES["SP"]["geocodes"])

        assert not df_rj.empty
        assert not df_sp.empty
        assert set(df_rj["municipio_geocodigo"].unique()) == rj_codes
        assert set(df_sp["municipio_geocodigo"].unique()) == sp_codes

    @pytest.mark.django_db(transaction=True)
    def test_dengue_returns_all_cities(
        self, episcanner_data_tables: None
    ) -> None:
        from dados.tasks import _fetch_alert_data

        df = _fetch_alert_data("RJ", "dengue", TEST_YEAR)

        assert len(df) == 20  # 2 cities x 10 weeks

    @pytest.mark.django_db(transaction=True)
    def test_chik_returns_data(self, episcanner_data_tables: None) -> None:
        from dados.tasks import _fetch_alert_data

        df = _fetch_alert_data("RJ", "chik", TEST_YEAR)

        assert not df.empty
        assert len(df) == 20

    @pytest.mark.django_db(transaction=True)
    def test_zika_returns_data(self, episcanner_data_tables: None) -> None:
        from dados.tasks import _fetch_alert_data

        df = _fetch_alert_data("SP", "zika", TEST_YEAR)

        assert not df.empty
        assert len(df) == 20

    @pytest.mark.django_db(transaction=True)
    def test_empty_for_unknown_state(
        self, episcanner_data_tables: None
    ) -> None:
        from dados.tasks import _fetch_alert_data

        df = _fetch_alert_data("AC", "dengue", TEST_YEAR)

        assert df.empty


class TestSaveSirParams:
    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_persists_multiple_cities(
        self,
        sir_params_table: None,
        mock_sir_params: list[SirParams],
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import _save_sir_params

        _save_sir_params("dengue", TEST_YEAR, mock_sir_params)

        assert EpiscannerSirParams.objects.using("dados").count() == 4
        for params in mock_sir_params:
            row = EpiscannerSirParams.objects.using("dados").get(
                cid10="A90",
                geocode_id=params.geocode,
                year=TEST_YEAR,
            )
            assert row.r0 == params.R0
            assert row.beta == params.beta
            assert row.total_cases == params.total_cases

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_persists_all_diseases(self, sir_params_table: None) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import _save_sir_params

        for disease in ("dengue", "chik", "zika"):
            params = [
                SirParams(
                    geocode=3304557,
                    year=TEST_YEAR,
                    ep_ini=f"{TEST_YEAR}05",
                    ep_pw=f"{TEST_YEAR}10",
                    peak_week=10.0,
                    beta=1.5,
                    gamma=0.5,
                    R0=3.0,
                    total_cases=1000.0,
                    alpha=0.95,
                    sum_res=50.0,
                )
            ]
            _save_sir_params(disease, TEST_YEAR, params)

        from dados.tasks import DISEASE_CID10

        for disease in ("dengue", "chik", "zika"):
            row = EpiscannerSirParams.objects.using("dados").get(
                cid10=DISEASE_CID10[disease],
                geocode_id=3304557,
                year=TEST_YEAR,
            )
            assert row.r0 == 3.0

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_update_or_create_overwrites(
        self,
        sir_params_table: None,
        mock_sir_params: list[SirParams],
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import _save_sir_params

        _save_sir_params("dengue", TEST_YEAR, mock_sir_params)

        updated = [
            SirParams(
                geocode=3304557,
                year=TEST_YEAR,
                ep_pw=f"{TEST_YEAR}11",
                peak_week=12.0,
                beta=2.0,
                gamma=0.3,
                R0=4.0,
                total_cases=2000.0,
                alpha=0.85,
                sum_res=100.0,
                t_ini=6,
                t_end=18,
            )
        ]
        _save_sir_params("dengue", TEST_YEAR, updated)

        count = (
            EpiscannerSirParams.objects.using("dados")
            .filter(
                cid10="A90",
                geocode_id=3304557,
                year=TEST_YEAR,
            )
            .count()
        )
        assert count == 1

        row = EpiscannerSirParams.objects.using("dados").get(
            cid10="A90",
            geocode_id=3304557,
            year=TEST_YEAR,
        )
        assert row.peak_week == 12.0
        assert row.beta == 2.0


class TestEpiscannerScanState:
    @pytest.mark.django_db
    def test_no_data_returns_early(self, episcanner_data_tables: None) -> None:
        from dados.tasks import episcanner_scan_state

        result = episcanner_scan_state.run("AC", "dengue", TEST_YEAR)

        assert "no data" in result

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_saves_richards_results_for_dengue(
        self,
        episcanner_data_tables: None,
        sir_params_table: None,
        mock_sir_params: list[SirParams],
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import episcanner_scan_state

        with patch(
            "dados.tasks.EpiScanner.richards",
            return_value=mock_sir_params,
        ):
            result = episcanner_scan_state.run("RJ", "dengue", TEST_YEAR)

        assert "4 cities saved" in result
        for params in mock_sir_params:
            row = EpiscannerSirParams.objects.using("dados").get(
                cid10="A90",
                geocode_id=params.geocode,
                year=TEST_YEAR,
            )
            assert row.r0 == params.R0

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_saves_richards_results_for_chik(
        self,
        episcanner_data_tables: None,
        sir_params_table: None,
        mock_sir_params: list[SirParams],
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import episcanner_scan_state

        with patch(
            "dados.tasks.EpiScanner.richards",
            return_value=mock_sir_params,
        ):
            result = episcanner_scan_state.run("RJ", "chik", TEST_YEAR)

        assert "4 cities saved" in result
        assert (
            EpiscannerSirParams.objects.using("dados")
            .filter(
                cid10="A92.0",
            )
            .count()
            == 4
        )

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_saves_richards_results_for_zika(
        self,
        episcanner_data_tables: None,
        sir_params_table: None,
        mock_sir_params: list[SirParams],
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import episcanner_scan_state

        with patch(
            "dados.tasks.EpiScanner.richards",
            return_value=mock_sir_params,
        ):
            result = episcanner_scan_state.run("SP", "zika", TEST_YEAR)

        assert "4 cities saved" in result
        assert (
            EpiscannerSirParams.objects.using("dados")
            .filter(
                cid10="A928",
            )
            .count()
            == 4
        )

    @pytest.mark.django_db(transaction=True, databases={"default", "dados"})
    def test_scans_multiple_ufs(
        self,
        episcanner_data_tables: None,
        sir_params_table: None,
    ) -> None:
        from dados.models import EpiscannerSirParams
        from dados.tasks import episcanner_scan_state

        rj_params = [
            SirParams(
                geocode=gc,
                year=TEST_YEAR,
                ep_pw=f"{TEST_YEAR}10",
                peak_week=10.0,
                beta=1.5,
                gamma=0.5,
                R0=3.0,
                total_cases=1000.0,
                alpha=0.95,
                sum_res=50.0,
            )
            for gc in CITIES["RJ"]["geocodes"]
        ]
        sp_params = [
            SirParams(
                geocode=gc,
                year=TEST_YEAR,
                ep_pw=f"{TEST_YEAR}10",
                peak_week=10.0,
                beta=1.5,
                gamma=0.5,
                R0=3.0,
                total_cases=1000.0,
                alpha=0.95,
                sum_res=50.0,
            )
            for gc in CITIES["SP"]["geocodes"]
        ]

        with patch(
            "dados.tasks.EpiScanner.richards",
            side_effect=[rj_params, sp_params],
        ):
            episcanner_scan_state.run("RJ", "dengue", TEST_YEAR)
            episcanner_scan_state.run("SP", "dengue", TEST_YEAR)

        assert EpiscannerSirParams.objects.using("dados").count() == 4


class TestEpiscannerAllStates:
    @pytest.mark.django_db
    def test_fans_out_to_all_states(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from dados.tasks import episcanner_all_states

        class _DelayStub:
            def __init__(self) -> None:
                self.calls: list[tuple] = []

            def delay(self, *args, **kwargs) -> None:
                self.calls.append(args)

        stub = _DelayStub()
        monkeypatch.setattr("dados.tasks.episcanner_scan_state", stub)

        episcanner_all_states.run(TEST_YEAR, "dengue")

        assert len(stub.calls) == 27
        state_abbrs = {call[0] for call in stub.calls}
        assert "RJ" in state_abbrs
        assert "SP" in state_abbrs
        assert all(call[1] == "dengue" for call in stub.calls)
        assert all(call[2] == TEST_YEAR for call in stub.calls)
