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

    def db_for_read(self, model, **hints):
        """"Point all read operations to the specific database."""
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
        db_obj1 = settings.DATABASE_APPS_MAPPING.get(obj1._meta.app_label)
        db_obj2 = settings.DATABASE_APPS_MAPPING.get(obj2._meta.app_label)

        allow = None

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
        return allow

    def allow_migrate(self, db, app_label, **hints):
        apps_mapping = settings.DATABASE_APPS_MAPPING  # alias
        allow = True

        if db in apps_mapping.values() and app_label in apps_mapping:
            allow = apps_mapping[app_label] == db

        if allow and app_label in settings.MIGRATION_MODULES:
            if settings.MIGRATION_MODULES[app_label] is None:
                allow = False
        print(db, app_label, allow)
        return allow
