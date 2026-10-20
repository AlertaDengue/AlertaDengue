"""Regression checks for the MinIO pipeline ingress contract."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

MINIO_COMPOSE = Path("containers/compose-minio.yaml")
ENV_TEMPLATE = Path(".envs/.env.tpl")


def test_minio_services_join_existing_network() -> None:
    base = yaml.safe_load(Path("containers/compose-base.yaml").read_text())
    services = yaml.safe_load(MINIO_COMPOSE.read_text())["services"]
    assert "infodengue" in base["networks"]
    for name in ("minio", "minio-init", "minio-materializer"):
        assert "infodengue" in services[name]["networks"]


@pytest.mark.parametrize(
    ("exclusion", "expected"),
    [
        (
            None,
            ["mirror", "--watch", "miniostore/sinan-infodengue", "/incoming"],
        ),
        (
            "",
            ["mirror", "--watch", "miniostore/sinan-infodengue", "/incoming"],
        ),
        (
            "approved-fixtures/*",
            [
                "mirror",
                "--watch",
                "--exclude",
                "approved-fixtures/*",
                "miniostore/sinan-infodengue",
                "/incoming",
            ],
        ),
    ],
)
def test_materializer_argv(
    tmp_path: Path, exclusion: str | None, expected: list[str]
) -> None:
    services = yaml.safe_load(MINIO_COMPOSE.read_text())["services"]
    entrypoint = services["minio-materializer"]["entrypoint"]
    assert entrypoint[:2] == ["/bin/sh", "-c"]
    assert "$${MINIO_MATERIALIZER_EXCLUDE}" in entrypoint[2]

    fake_mc = tmp_path / "mc"
    fake_mc.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "if sys.argv[1] == 'mirror':\n"
        "    with open(os.environ['MC_ARGV_FILE'], 'w') as output:\n"
        "        json.dump(sys.argv[1:], output)\n"
    )
    fake_mc.chmod(0o755)
    argv_file = tmp_path / "argv.json"
    environment = {
        **os.environ,
        "MINIO_ROOT_USER": "test-user",
        "MINIO_ROOT_PASSWORD": "test-password",
        "MC_ARGV_FILE": str(argv_file),
    }
    environment.pop("MINIO_MATERIALIZER_EXCLUDE", None)
    if exclusion is not None:
        environment["MINIO_MATERIALIZER_EXCLUDE"] = exclusion

    # Compose turns $$ into $ before passing the command to the container shell.
    command = (
        entrypoint[2].replace("$$", "$").replace("/usr/bin/mc", str(fake_mc))
    )
    subprocess.run(["/bin/sh", "-c", command], env=environment, check=True)
    assert json.loads(argv_file.read_text()) == expected


@pytest.mark.parametrize("exclusion", [None, "approved-fixtures/*"])
def test_env_template_substitution(exclusion: str | None) -> None:
    template = ENV_TEMPLATE.read_text()
    assert (
        "MINIO_MATERIALIZER_EXCLUDE=${MINIO_MATERIALIZER_EXCLUDE}" in template
    )
    environment = os.environ.copy()
    environment.pop("MINIO_MATERIALIZER_EXCLUDE", None)
    if exclusion is not None:
        environment["MINIO_MATERIALIZER_EXCLUDE"] = exclusion
    result = subprocess.run(
        ["envsubst", "${MINIO_MATERIALIZER_EXCLUDE}"],
        input=template,
        text=True,
        capture_output=True,
        check=True,
        env=environment,
    )
    assert f"MINIO_MATERIALIZER_EXCLUDE={exclusion or ''}\n" in result.stdout


def test_incoming_mount_is_unchanged() -> None:
    services = yaml.safe_load(MINIO_COMPOSE.read_text())["services"]
    assert (
        "${DOCKER_HOST_INCOMING_DIR}:/incoming"
        in services["minio-materializer"]["volumes"]
    )
