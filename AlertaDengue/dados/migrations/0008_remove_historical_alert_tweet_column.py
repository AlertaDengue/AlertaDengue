"""Remove the obsolete tweet values from historical-alert tables."""

from django.db import migrations


class Migration(migrations.Migration):
    """Drop a retired AlertTools output from each disease history table."""

    atomic = True

    dependencies = [
        ("dados", "0007_retained_referenced_adapters"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE "Municipio"."Historico_alerta"
                DROP COLUMN "tweet";
                ALTER TABLE "Municipio"."Historico_alerta_chik"
                DROP COLUMN "tweet";
                ALTER TABLE "Municipio"."Historico_alerta_zika"
                DROP COLUMN "tweet";
            """,
            reverse_sql=None,
        ),
    ]
