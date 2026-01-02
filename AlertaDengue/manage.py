# type: ignore
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main() -> None:
    """Run administrative tasks.

    The settings module is read from the ``DJANGO_SETTINGS_MODULE``
    environment variable. When it is not defined, we default to the
    development settings (``ad_main.settings.dev``).
    """
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "ad_main.settings.dev"),
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        msg = (
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        )
        raise ImportError(msg) from exc

    project_root: Path = Path(__file__).parent.resolve()
    sys.path.append(str(project_root / "AlertaDengue"))

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
