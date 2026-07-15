from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.template.utils import get_app_template_dirs
import pytest


@pytest.mark.parametrize(
    "template_name",
    sorted(
        {
            path.relative_to(template_dir).as_posix()
            for template_dir in (
                *(Path(path) for path in settings.TEMPLATES[0]["DIRS"]),
                *get_app_template_dirs("templates"),
            )
            if template_dir.exists()
            for path in template_dir.rglob("*.html")
        }
    ),
)
def test_django_template_compiles(template_name: str) -> None:
    get_template(template_name)
