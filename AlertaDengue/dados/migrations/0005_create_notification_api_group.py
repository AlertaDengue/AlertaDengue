from django.db import migrations

GROUP_NAME = "Notification API Users"


def create_notification_api_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GROUP_NAME)


def delete_notification_api_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("dados", "0004_load_parameters_uf_2025"),
    ]

    operations = [
        migrations.RunPython(
            create_notification_api_group,
            delete_notification_api_group,
        ),
    ]
