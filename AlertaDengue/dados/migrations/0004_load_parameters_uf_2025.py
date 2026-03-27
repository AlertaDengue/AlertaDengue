from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from django.db import migrations

STATE_MAP: dict[str, tuple[int, str, str]] = {
    "Rondônia": (11, "RO", "Rondônia"),
    "Acre": (12, "AC", "Acre"),
    "Amazonas": (13, "AM", "Amazonas"),
    "Roraima": (14, "RR", "Roraima"),
    "Pará": (15, "PA", "Pará"),
    "Amapá": (16, "AP", "Amapá"),
    "Tocantins": (17, "TO", "Tocantins"),
    "Maranhão": (21, "MA", "Maranhão"),
    "Piauí": (22, "PI", "Piauí"),
    "Ceará": (23, "CE", "Ceará"),
    "Rio Grande do Norte": (24, "RN", "Rio Grande do Norte"),
    "Paraíba": (25, "PB", "Paraíba"),
    "Pernambuco": (26, "PE", "Pernambuco"),
    "Alagoas": (27, "AL", "Alagoas"),
    "Sergipe": (28, "SE", "Sergipe"),
    "Bahia": (29, "BA", "Bahia"),
    "Minas Gerais": (31, "MG", "Minas Gerais"),
    "Espírito Santo": (32, "ES", "Espírito Santo"),
    "Rio de Janeiro": (33, "RJ", "Rio de Janeiro"),
    "São Paulo": (35, "SP", "São Paulo"),
    "Paraná": (41, "PR", "Paraná"),
    "Santa Catarina": (42, "SC", "Santa Catarina"),
    "Rio Grande do Sul": (43, "RS", "Rio Grande do Sul"),
    "Mato Grosso do Sul": (50, "MS", "Mato Grosso do Sul"),
    "Mato Grosso": (51, "MT", "Mato Grosso"),
    "Goiás": (52, "GO", "Goiás"),
    "Distrito Federal": (53, "DF", "Distrito Federal"),
}


def _data_dir() -> Path:
    """Return the directory containing the UF threshold CSV files."""
    return Path(__file__).resolve().parent.parent / "data" / "parameters_uf"


def _to_float(value: str) -> float | None:
    """Convert a CSV numeric field to float or None."""
    cleaned = value.strip()
    if not cleaned:
        return None
    return float(cleaned)


def _load_dataset(
    parameter_uf_model: Any,
    db_alias: str,
    csv_path: Path,
) -> set[str]:
    """Load one seasonal dataset into ParameterUF."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV dataset not found: {csv_path}")

    seen_cid10: set[str] = set()

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            csv_state_name = row["nome"].strip()
            if csv_state_name not in STATE_MAP:
                raise ValueError(
                    f"Unknown state name in {csv_path.name}: "
                    f"{csv_state_name}"
                )

            state_code, state_abbr, state_name = STATE_MAP[csv_state_name]
            cid10 = row["cid10"].strip()
            seen_cid10.add(cid10)

            parameter_uf_model.objects.using(db_alias).update_or_create(
                state_code=state_code,
                cid10=cid10,
                defaults={
                    "state_abbr": state_abbr,
                    "state_name": state_name,
                    "limiar_preseason": _to_float(row["pre"]),
                    "limiar_posseason": _to_float(row["pos"]),
                    "limiar_epidemico": _to_float(row["veryhigh"]),
                },
            )

    return seen_cid10


def _ensure_es_placeholders(
    parameter_uf_model: Any,
    db_alias: str,
    cid10_codes: set[str],
) -> None:
    """Ensure Espírito Santo exists with NULL thresholds when absent."""
    state_code, state_abbr, state_name = STATE_MAP["Espírito Santo"]

    for cid10 in cid10_codes:
        parameter_uf_model.objects.using(db_alias).update_or_create(
            state_code=state_code,
            cid10=cid10,
            defaults={
                "state_abbr": state_abbr,
                "state_name": state_name,
                "limiar_preseason": None,
                "limiar_posseason": None,
                "limiar_epidemico": None,
            },
        )


def load_parameters_uf_mem2025(
    apps: migrations.state.StateApps,
    schema_editor: Any,
) -> None:
    """Load the stored 2025 UF threshold datasets."""
    parameter_uf_model = apps.get_model("dados", "ParameterUF")
    db_alias = schema_editor.connection.alias
    data_dir = _data_dir()

    csv_files = (
        data_dir / "mem2025_dengue_UF.csv",
        data_dir / "mem2025_chik_UF.csv",
    )

    seen_cid10: set[str] = set()
    for csv_path in csv_files:
        seen_cid10.update(
            _load_dataset(
                parameter_uf_model=parameter_uf_model,
                db_alias=db_alias,
                csv_path=csv_path,
            )
        )

    _ensure_es_placeholders(
        parameter_uf_model=parameter_uf_model,
        db_alias=db_alias,
        cid10_codes=seen_cid10,
    )


def unload_parameters_uf_mem2025(
    apps: migrations.state.StateApps,
    schema_editor: Any,
) -> None:
    """Remove rows loaded by the stored 2025 UF threshold datasets."""
    parameter_uf_model = apps.get_model("dados", "ParameterUF")
    db_alias = schema_editor.connection.alias

    parameter_uf_model.objects.using(db_alias).filter(
        cid10__in=["A90", "A92.0"],
    ).delete()


class Migration(migrations.Migration):
    """Load the stored 2025 UF threshold datasets."""

    dependencies = [
        ("dados", "0003_alter_parameteruf_cid10"),
    ]

    operations = [
        migrations.RunPython(
            load_parameters_uf_mem2025,
            reverse_code=unload_parameters_uf_mem2025,
        ),
    ]
