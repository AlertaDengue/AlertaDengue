__version__ = "4.2.3"  # semantic-release

from ad_main.celeryapp import app as celery_app

__all__ = ("celery_app",)
