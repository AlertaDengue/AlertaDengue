from __future__ import annotations

from typing import Any

from django.db import migrations

# Distrito Federal uses the MEM2025 municipal thresholds calculated for
# Brasília (IBGE geocode 5300108), validated against Dengue_global.parameters.
DF_THRESHOLDS = {
    "A90": {
        "limiar_preseason": 12.6688586706146,
        "limiar_posseason": 14.2228978596959,
        "limiar_epidemico": 76.6305102857116,
    },
    "A92.0": {
        "limiar_preseason": 0.368068592796877,
        "limiar_posseason": 0.292548628366393,
        "limiar_epidemico": 1.26462573983109,
    },
}


def add_df_uf_epidemic_thresholds(
    apps: migrations.state.StateApps,
    schema_editor: Any,
) -> None:
    parameter_uf_model = apps.get_model("dados", "ParameterUF")
    db_alias = schema_editor.connection.alias

    for cid10, thresholds in DF_THRESHOLDS.items():
        parameter_uf_model.objects.using(db_alias).update_or_create(
            state_code=53,
            cid10=cid10,
            defaults={
                "state_abbr": "DF",
                "state_name": "Distrito Federal",
                **thresholds,
            },
        )


def remove_df_uf_epidemic_thresholds(
    apps: migrations.state.StateApps,
    schema_editor: Any,
) -> None:
    parameter_uf_model = apps.get_model("dados", "ParameterUF")
    db_alias = schema_editor.connection.alias

    parameter_uf_model.objects.using(db_alias).filter(
        state_code=53,
        cid10__in=list(DF_THRESHOLDS),
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dados", "0008_remove_historical_alert_tweet_column"),
    ]

    operations = [
        migrations.RunPython(
            add_df_uf_epidemic_thresholds,
            reverse_code=remove_df_uf_epidemic_thresholds,
        ),
    ]
