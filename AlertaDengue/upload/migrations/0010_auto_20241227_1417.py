# Generated by Django 3.2.25 on 2024-12-27 14:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("upload", "0009_auto_20241212_0357"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sinanupload",
            name="file",
        ),
        migrations.RemoveField(
            model_name="sinanupload",
            name="uploaded_by",
        ),
        migrations.AddField(
            model_name="sinanupload",
            name="upload",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="upload.sinanchunkedupload",
            ),
        ),
    ]
