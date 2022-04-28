from django.conf import settings


class DatabaseAppsRouter(object):
    """
    A router to control all database operations on models for different
    databases.

    In case an app is not set in settings.DATABASE_APPS_MAPPING, the router
    will fallback to the `default` database.

    Settings example:

    DATABASE_APPS_MAPPING = {'app1': 'db1', 'app2': 'db2'}
    """

    core_apps = {"contenttypes", "auth"}

    def db_for_read(self, model, **hints):
        """ "Point all read operations to the specific database."""
        db = None
        if model._meta.app_label in settings.DATABASE_APPS_MAPPING:
            db = settings.DATABASE_APPS_MAPPING[model._meta.app_label]
        return db

    def db_for_write(self, model, **hints):
        """Point all write operations to the specific database."""
        db = None
        if model._meta.app_label in settings.DATABASE_APPS_MAPPING:
            db = settings.DATABASE_APPS_MAPPING[model._meta.app_label]
        return db

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation between apps that use the same database."""
        label1 = obj1._meta.app_label
        label2 = obj2._meta.app_label

        db_obj1 = settings.DATABASE_APPS_MAPPING.get(label1)
        db_obj2 = settings.DATABASE_APPS_MAPPING.get(label2)

        allow = None

        # Allow core and 3rd-party relationships here
        set_1 = {label1, label2}
        if self.core_apps - set_1 != self.core_apps:
            return True

        if db_obj1 and db_obj2:
            allow = True if db_obj1 == db_obj2 else False

        return allow

    def allow_syncdb(self, db, model):
        """Make sure that apps only appear in the related database."""
        allow = None
        apps_mapping = settings.DATABASE_APPS_MAPPING  # alias

        if db in apps_mapping.values():
            allow = apps_mapping.get(model._meta.app_label) == db
        elif model._meta.app_label in apps_mapping:
            allow = False

        # Allow core and 3rd-party relationships here
        set_1 = {model._meta.app_label}
        if self.core_apps - set_1 != self.core_apps:
            return True

        return allow

    def allow_migrate(self, db, app_label, **hints):
        apps_mapping = settings.DATABASE_APPS_MAPPING  # alias
        allow = True

        if "target_db" in hints:
            return db == hints["target_db"]

        if db in apps_mapping.values() and app_label in apps_mapping:
            allow = apps_mapping[app_label] == db

        if allow and app_label in settings.MIGRATION_MODULES:
            if settings.MIGRATION_MODULES[app_label] is None:
                allow = False
        # Allow core and 3rd-party relationships here
        set_1 = {app_label}
        if self.core_apps - set_1 != self.core_apps:
            return True
        return allow
