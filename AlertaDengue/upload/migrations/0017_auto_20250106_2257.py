# Generated by Django 3.2.25 on 2025-01-06 22:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("upload", "0016_auto_20250106_1428"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sinanuploadlogstatus",
            name="end_id",
        ),
        migrations.RemoveField(
            model_name="sinanuploadlogstatus",
            name="inserts",
        ),
        migrations.RemoveField(
            model_name="sinanuploadlogstatus",
            name="start_id",
        ),
        migrations.RemoveField(
            model_name="sinanuploadlogstatus",
            name="time_spend",
        ),
        migrations.RemoveField(
            model_name="sinanuploadlogstatus",
            name="updates",
        ),
    ]
