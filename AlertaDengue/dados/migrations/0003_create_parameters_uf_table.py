from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dados", "0002_alter_cid10_options_alter_city_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE "Dengue_global"."parameters_uf" (
                    state_code INTEGER NOT NULL,
                    state_abbr VARCHAR(2) NOT NULL,
                    state_name TEXT NOT NULL,
                    cid10 VARCHAR NOT NULL,
                    limiar_preseason DOUBLE PRECISION,
                    limiar_posseason DOUBLE PRECISION,
                    limiar_epidemico DOUBLE PRECISION,
                    PRIMARY KEY (state_code, cid10)
                );

                CREATE INDEX IF NOT EXISTS parameters_uf_idx_state_code
                ON "Dengue_global"."parameters_uf"(state_code);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS "Dengue_global"."parameters_uf";
            """,
        ),
    ]
