"""Exercise the local Bash operation and real Django commands with service doubles."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKER_DOUBLE = r"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

args = sys.argv[1:]
fault = os.environ.get("RUNTIME_TEST_FAULT", "")
root = Path(os.environ["RUNTIME_TEST_ROOT"])
sql = sys.stdin.read() if "postgres" in args else ""
preflight = "python" in args and "manage.py" not in args
with Path(os.environ["RUNTIME_TEST_LOG"]).open("a") as log:
    log.write(json.dumps({"command": Path(sys.argv[0]).name,
                          "args": args, "sql": sql,
                          "env": os.environ.get("ENV"),
                          "preflight": preflight}) + "\n")
if "python" in args and "manage.py" not in args:
    index = args.index("-c")
    sys.exit(subprocess.run([sys.executable, "-c", *args[index + 1:]]).returncode)
elif "postgres" in args:
    if sql.startswith("BEGIN;"):
        if fault == "refresh":
            sys.exit(7)
    else:
        print("f" if fault == "week" else "t")
elif "collectstatic" in args:
    if fault == "collectstatic":
        sys.exit(8)
    subprocess.run([sys.executable, "-c", '''
import sys
import django
from django.conf import settings
from django.core.management import call_command
settings.configure(INSTALLED_APPS=["django.contrib.staticfiles"],
                   STATIC_URL="/static/", STATICFILES_DIRS=[sys.argv[1]],
                   STATIC_ROOT=sys.argv[2])
django.setup()
call_command("collectstatic", interactive=False, verbosity=0)
''', str(root / "AlertaDengue/static"), str(root / "collected")], check=True)
    for disease in ("dengue", "chikungunya"):
        if fault == "collected_hash_" + disease:
            (root / ("collected/img/incidence_maps/country/incidence_Nacional_"
                     + disease + ".png")).write_bytes(b"stale")
elif "shell" in args:
    if fault == "cache":
        sys.exit(9)
    subprocess.run([sys.executable, "-c", '''
from django.conf import settings
settings.configure(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
''' + args[-1]], check=True)
elif "sha256sum" in args:
    path = root / "collected" / args[-1].removeprefix("/opt/services/staticfiles/")
    print(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + args[-1])
else:
    raise AssertionError(args)
"""


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path / "repository"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts/refresh_runtime.sh"
    shutil.copy2(ROOT / "scripts/refresh_runtime.sh", script)
    (root / ".envs").mkdir()
    (root / ".envs/.env").write_text("ENV=dev\n")
    maps = root / "AlertaDengue/static/img/incidence_maps"
    (maps / "country").mkdir(parents=True)
    for disease in ("dengue", "chikungunya"):
        (maps / f"country/incidence_Nacional_{disease}.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + disease.encode()
        )
    (maps / "untouched.png").write_bytes(b"old")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "docker"
    executable.write_text(f"#!{sys.executable}\n" + DOCKER_DOUBLE)
    executable.chmod(0o755)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("INFODENGUE_")
    }
    env.update(
        PATH=f"{bin_dir}:{env['PATH']}",
        RUNTIME_TEST_ROOT=str(root),
        RUNTIME_TEST_LOG=str(tmp_path / "commands.jsonl"),
    )

    class RuntimeRefresh:
        def run(self, args=None, fault="", profile="staging", **variables):
            if args is None:
                args = [
                    "--env",
                    profile,
                    "--week",
                    "202638",
                ]
            return subprocess.run(
                ["bash", str(script), *args],
                env={**env, "RUNTIME_TEST_FAULT": fault, **variables},
                capture_output=True,
                text=True,
                check=False,
            )

        def all_commands(self):
            log = Path(env["RUNTIME_TEST_LOG"])
            return (
                [json.loads(line) for line in log.read_text().splitlines()]
                if log.exists()
                else []
            )

        def commands(self):
            """Return workflow commands, excluding read-only input checks."""
            return [
                item
                for item in self.all_commands()
                if not item.get("preflight")
            ]

    instance = RuntimeRefresh()
    instance.root = root
    instance.maps = maps
    return instance


@pytest.mark.parametrize("missing", ["--env", "--week"])
def test_missing_required_argument_does_not_modify_state(runtime, missing):
    options = {
        "--env": "staging",
        "--week": "202638",
    }
    args = [
        value
        for key, item in options.items()
        if key != missing
        for value in (key, item)
    ]
    result = runtime.run(args)
    assert result.returncode == 2
    assert f"Missing {missing}" in result.stderr
    assert runtime.commands() == []
    assert (runtime.maps / "untouched.png").exists()


@pytest.mark.parametrize(
    "option,value",
    [
        ("--env", "unknown"),
        ("--week", "20263"),
        ("--week", "2026380"),
        ("--week", "2026xx"),
        ("--week", "202638;echo bad"),
        ("--week", "202654"),
        ("--week", "202600"),
    ],
)
def test_invalid_arguments_does_not_modify_state(runtime, option, value):
    args = [
        "--env",
        "staging",
        "--week",
        "202638",
    ]
    args[args.index(option) + 1] = value
    result = runtime.run(args)
    assert result.returncode == 2
    assert "Invalid" in result.stderr
    assert runtime.commands() == []


@pytest.mark.parametrize(
    "artifact,empty",
    [
        ("country/incidence_Nacional_dengue.png", False),
        ("country/incidence_Nacional_chikungunya.png", False),
        ("country/incidence_Nacional_dengue.png", True),
        ("country/incidence_Nacional_chikungunya.png", True),
    ],
)
def test_missing_or_empty_artifacts_stop_before_refresh(
    runtime, artifact, empty
):
    target = runtime.maps / artifact
    if empty:
        target.write_bytes(b"")
    elif target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    result = runtime.run()
    assert result.returncode != 0
    assert runtime.commands() == []
    assert (runtime.maps / "untouched.png").exists()


def test_refresh_failure_stops_before_collectstatic(runtime):
    result = runtime.run(fault="refresh")
    assert result.returncode != 0
    assert len(runtime.commands()) == 1
    assert (runtime.maps / "untouched.png").exists()


@pytest.mark.parametrize("profile", ["dev", "staging", "prod"])
def test_success_refreshes_collects_clears_and_validates(runtime, profile):
    result = runtime.run(profile=profile)
    assert result.returncode == 0, result.stderr
    assert len(runtime.all_commands()) == 7
    assert "Week.fromstring" in runtime.all_commands()[0]["args"][-2]
    commands = runtime.commands()
    refresh, collect, clear, weeks, *hashes = commands
    assert refresh["env"] == profile
    assert f"infodengue-{profile}" in refresh["args"]
    assert "psql -v ON_ERROR_STOP=1" in " ".join(refresh["args"])
    assert refresh["sql"].startswith("BEGIN;")
    assert refresh["sql"].endswith("COMMIT;\n")
    assert refresh["sql"].count("REFRESH MATERIALIZED VIEW") == 6
    for view in (
        "hist_uf_dengue",
        "hist_uf_chik",
        "hist_uf_zika",
        "city_count_by_uf_dengue",
        "city_count_by_uf_chikungunya",
        "city_count_by_uf_zika",
    ):
        assert f"public.{view}_materialized_view;" in refresh["sql"]
    assert collect["args"][-4:] == [
        "python",
        "manage.py",
        "collectstatic",
        "--no-input",
    ]
    assert "cache.clear()" in clear["args"][-1]
    assert '"Municipio"."Historico_alerta"' in weeks["sql"]
    assert "public.hist_uf_dengue_materialized_view" in weeks["sql"]
    assert weeks["sql"].count('MAX("SE")::integer') == 2
    assert weeks["sql"].count("= :'requested_week'::integer") == 2
    assert weeks["sql"].count("COALESCE") == 2
    assert "requested_week=202638" in weeks["args"]
    assert "-c" not in weeks["args"][weeks["args"].index("-tA") :]
    assert len(hashes) == 2
    for call, disease in zip(hashes, ("dengue", "chikungunya"), strict=True):
        filename = f"incidence_Nacional_{disease}.png"
        assert (
            call["args"][-1]
            == f"/opt/services/staticfiles/img/incidence_maps/country/{filename}"
        )
        assert (
            runtime.root / f"collected/img/incidence_maps/country/{filename}"
        ).read_bytes() == (runtime.maps / "country" / filename).read_bytes()
    assert (runtime.maps / "untouched.png").read_bytes() == b"old"
    sugar = yaml.safe_load((ROOT / ".sugar.yaml").read_text())
    args = refresh["args"]
    files = [args[i + 1] for i, arg in enumerate(args) if arg == "--file"]
    assert files == sugar["profiles"][profile]["config-path"]


def test_failed_collectstatic_does_not_invalidate_cache(runtime):
    result = runtime.run(fault="collectstatic")
    assert result.returncode != 0
    assert "collectstatic" in result.stderr
    assert len(runtime.commands()) == 2
    assert all("shell" not in call["args"] for call in runtime.commands())


@pytest.mark.parametrize(
    "fault,message",
    [
        ("collected_hash_dengue", "Collected map SHA256 mismatch"),
        ("collected_hash_chikungunya", "Collected map SHA256 mismatch"),
        ("week", "Database postconditions"),
        ("cache", "clear Django cache"),
    ],
)
def test_postcondition_and_cache_failures_do_not_report_success(
    runtime, fault, message
):
    result = runtime.run(fault=fault)
    assert result.returncode != 0
    assert message in result.stderr
    assert "succeeded" not in result.stdout


@pytest.mark.parametrize("profile", ["staging", "prod"])
def test_web_static_root_bind_mount(profile):
    # Render the real merged Compose configuration without starting containers.
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".envs/.env",
            "--file",
            "containers/compose-base.yaml",
            "--file",
            f"containers/compose-{profile}.yaml",
            "--file",
            "containers/compose-minio.yaml",
            "--file",
            "containers/compose-pgbackrest.yaml",
            "--project-name",
            f"infodengue-{profile}",
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "ENV": profile},
    )
    web = json.loads(result.stdout)["services"]["web"]
    assert web["environment"]["ENV"] == profile
    assert (
        web["environment"]["DJANGO_SETTINGS_MODULE"]
        == f"ad_main.settings.{profile}"
    )
    mounts = {mount["target"]: mount for mount in web["volumes"]}
    mount = mounts["/opt/services/staticfiles"]
    assert mount["type"] == "bind"
    assert Path(mount["source"]) == ROOT / "staticfiles"
    assert not mount.get("read_only", False)
    assert (
        Path(mounts["/opt/services/AlertaDengue"]["source"])
        == ROOT / "AlertaDengue"
    )
    assert "/opt/services/ingestion/sinan" in mounts
    assert "/opt/services/ingestion/sinan/imported" in mounts
    if profile == "prod":
        assert mounts["/opt/services/technical_reports"]["read_only"]


def test_makim_task_delegates_with_named_arguments():
    config = yaml.safe_load((ROOT / ".makim.yaml").read_text())
    task = config["groups"]["deployment"]["tasks"]["refresh-runtime"]
    assert set(task["args"]) == {"env", "week"}
    assert all(task["args"][name]["required"] for name in ("env", "week"))
    assert task["run"].startswith("scripts/refresh_runtime.sh")
    for name in ("env", "week"):
        assert (
            f'--{name} "${{{{ args.{name.replace("-", "_")} }}}}"'
            in task["run"]
        )


def test_semantically_invalid_week_stops_at_read_only_validation(runtime):
    result = runtime.run(
        [
            "--env",
            "staging",
            "--week",
            "202654",
        ]
    )
    assert result.returncode == 2
    assert "Invalid --week" in result.stderr
    assert runtime.commands() == []
    checks = runtime.all_commands()
    assert len(checks) == 1
    assert "Week.fromstring" in checks[0]["args"][-2]
    assert (runtime.maps / "untouched.png").read_bytes() == b"old"


def test_cache_clear_returning_none_is_accepted(runtime):
    from django.core.cache.backends.locmem import LocMemCache

    assert LocMemCache("runtime-test", {}).clear() is None
    result = runtime.run()
    assert result.returncode == 0, result.stderr
    assert (
        runtime.commands()[2]["args"][-1]
        == "from django.core.cache import cache; cache.clear()"
    )


def test_cache_command_failure_stops_before_local_validation(runtime):
    result = runtime.run(fault="cache")
    assert result.returncode == 9
    assert len(runtime.commands()) == 3
    assert "succeeded" not in result.stdout


def test_deployment_components_are_producer_independent():
    deployment = yaml.safe_load((ROOT / ".makim.yaml").read_text())["groups"][
        "deployment"
    ]
    components = {
        "deployment task": yaml.safe_dump(deployment),
        "script": (ROOT / "scripts/refresh_runtime.sh").read_text(),
        "documentation": (
            ROOT / "docs/deployment/runtime-refresh.md"
        ).read_text(),
    }
    forbidden = (
        "AlertaDengueAnalise",
        "maps-source",
        "INFODENGUE_WEB_ORIGIN",
        "INFODENGUE_WEB_HOST",
        "INFODENGUE_NGINX_CONTAINER",
        "INFODENGUE_NGINX_CACHE_PATH",
        "finalize-analysis",
        "finalize_analysis_run",
        "pipeline.refresh-alertas-job",
        "rsync",
        "curl",
    )
    for name, content in components.items():
        for token in forbidden:
            assert token not in content, f"{name} references {token}"
