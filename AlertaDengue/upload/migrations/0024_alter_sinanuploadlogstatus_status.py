# Generated by Django 3.2.25 on 2025-05-19 21:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("upload", "0023_alter_sinanuploadlogstatus_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sinanuploadlogstatus",
            name="status",
            field=models.IntegerField(
                choices=[
                    (0, "Pending"),
                    (1, "Success"),
                    (2, "Error"),
                    (3, "Success with residues"),
                ],
                default=0,
            ),
        ),
    ]
