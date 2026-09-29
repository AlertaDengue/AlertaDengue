"""Exercise Bash, rsync, collectstatic and HTTP with Compose service doubles."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread

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
fault = os.environ.get("FINALIZER_TEST_FAULT", "")
root = Path(os.environ["FINALIZER_TEST_ROOT"])
sql = sys.stdin.read() if "postgres" in args else ""
preflight = "port" in args or ("python" in args and "manage.py" not in args)
with Path(os.environ["FINALIZER_TEST_LOG"]).open("a") as log:
    log.write(json.dumps({"command": Path(sys.argv[0]).name,
                          "args": args, "sql": sql,
                          "env": os.environ.get("ENV"),
                          "preflight": preflight}) + "\n")
if "port" in args:
    print("0.0.0.0:" + os.environ.get("FINALIZER_TEST_WEB_PORT", "8000"))
elif "python" in args and "manage.py" not in args:
    index = args.index("-c")
    sys.exit(subprocess.run([sys.executable, "-c", *args[index + 1:]]).returncode)
elif Path(sys.argv[0]).name == "rsync":
    if fault == "rsync":
        sys.exit(11)
    subprocess.run([os.environ["FINALIZER_TEST_RSYNC"], *args], check=True)
    if fault == "published_hash":
        (Path(args[-1]) / "country/incidence_Nacional_dengue.png").write_bytes(b"stale")
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
elif "exec" in args and "find" in args:
    if fault == "nginx":
        sys.exit(10)
else:
    raise AssertionError(args)
"""


@pytest.fixture
def finalizer(tmp_path):
    root = tmp_path / "repository"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts/finalize_analysis_run.sh"
    shutil.copy2(ROOT / "scripts/finalize_analysis_run.sh", script)
    (root / ".envs").mkdir()
    (root / ".envs/.env").write_text("ENV=dev\n")
    maps = tmp_path / "analysis artifacts"
    (maps / "country").mkdir(parents=True)
    (maps / "state").mkdir()
    for disease in ("dengue", "chikungunya"):
        (maps / f"country/incidence_Nacional_{disease}.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + disease.encode()
        )
    (maps / "state/RJ.png").write_bytes(b"state map")
    published = root / "AlertaDengue/static/img/incidence_maps"
    published.mkdir(parents=True)
    (published / "obsolete.png").write_bytes(b"old")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("docker", "rsync"):
        executable = bin_dir / name
        executable.write_text(f"#!{sys.executable}\n" + DOCKER_DOUBLE)
        executable.chmod(0o755)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("INFODENGUE_")
    }
    env.update(
        PATH=f"{bin_dir}:{env['PATH']}",
        FINALIZER_TEST_ROOT=str(root),
        FINALIZER_TEST_LOG=str(tmp_path / "commands.jsonl"),
        FINALIZER_TEST_RSYNC=shutil.which("rsync"),
    )

    class Finalizer:
        def run(self, args=None, fault="", profile="staging", **variables):
            if args is None:
                args = [
                    "--env",
                    profile,
                    "--week",
                    "202638",
                    "--maps-source",
                    str(maps),
                ]
            return subprocess.run(
                ["bash", str(script), *args],
                env={**env, "FINALIZER_TEST_FAULT": fault, **variables},
                capture_output=True,
                text=True,
                check=False,
            )

        def all_commands(self):
            log = Path(env["FINALIZER_TEST_LOG"])
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

        def record_origin(self, path):
            with Path(env["FINALIZER_TEST_LOG"]).open("a") as log:
                log.write(
                    json.dumps({"command": "http", "args": [path]}) + "\n"
                )

    instance = Finalizer()
    instance.root = root
    instance.maps = maps
    instance.published = published
    return instance


@pytest.mark.parametrize("missing", ["--env", "--week", "--maps-source"])
def test_missing_required_argument_does_not_modify_state(finalizer, missing):
    options = {
        "--env": "staging",
        "--week": "202638",
        "--maps-source": str(finalizer.maps),
    }
    args = [
        value
        for key, item in options.items()
        if key != missing
        for value in (key, item)
    ]
    result = finalizer.run(args)
    assert result.returncode == 2
    assert f"Missing {missing}" in result.stderr
    assert finalizer.commands() == []
    assert (finalizer.published / "obsolete.png").exists()


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
def test_invalid_arguments_does_not_modify_state(finalizer, option, value):
    args = [
        "--env",
        "staging",
        "--week",
        "202638",
        "--maps-source",
        str(finalizer.maps),
    ]
    args[args.index(option) + 1] = value
    result = finalizer.run(args)
    assert result.returncode == 2
    assert "Invalid" in result.stderr
    assert finalizer.commands() == []


@pytest.mark.parametrize(
    "artifact,empty",
    [
        ("country/incidence_Nacional_dengue.png", False),
        ("country/incidence_Nacional_chikungunya.png", False),
        ("country/incidence_Nacional_dengue.png", True),
        ("country/incidence_Nacional_chikungunya.png", True),
        ("state", False),
        ("state/RJ.png", False),
        (".", False),
    ],
)
def test_missing_or_empty_artifacts_stop_before_refresh(
    finalizer, artifact, empty
):
    target = finalizer.maps / artifact
    if empty:
        target.write_bytes(b"")
    elif target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    result = finalizer.run()
    assert result.returncode != 0
    assert finalizer.commands() == []
    assert (finalizer.published / "obsolete.png").exists()


def test_refresh_failure_stops_before_publish(finalizer):
    result = finalizer.run(fault="refresh")
    assert result.returncode != 0
    assert len(finalizer.commands()) == 1
    assert (finalizer.published / "obsolete.png").exists()


@pytest.mark.parametrize("profile", ["dev", "staging"])
def test_success_refreshes_publishes_collects_clears_and_validates(
    finalizer, profile
):
    result = finalizer.run(profile=profile)
    assert result.returncode == 0, result.stderr
    commands = finalizer.commands()
    refresh, publish, collect, clear, weeks, *hashes = commands
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
    assert publish["command"] == "rsync"
    assert publish["args"][:2] == ["-a", "--delete"]
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
    assert not (finalizer.published / "obsolete.png").exists()
    sugar = yaml.safe_load((ROOT / ".sugar.yaml").read_text())
    args = refresh["args"]
    files = [args[i + 1] for i, arg in enumerate(args) if arg == "--file"]
    assert files == sugar["profiles"][profile]["config-path"]


def test_failed_collectstatic_does_not_invalidate_cache(finalizer):
    result = finalizer.run(fault="collectstatic")
    assert result.returncode != 0
    assert "collectstatic" in result.stderr
    assert len(finalizer.commands()) == 3
    assert all("shell" not in call["args"] for call in finalizer.commands())


@pytest.mark.parametrize(
    "fault,message",
    [
        ("published_hash", "Published map SHA256 mismatch"),
        ("collected_hash_dengue", "Collected map SHA256 mismatch"),
        ("collected_hash_chikungunya", "Collected map SHA256 mismatch"),
        ("week", "Database postconditions"),
        ("cache", "clear Django cache"),
    ],
)
def test_postcondition_and_cache_failures_do_not_report_success(
    finalizer, fault, message
):
    result = finalizer.run(fault=fault)
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


@pytest.fixture
def origin(finalizer):
    requests = []
    behavior = {"stale": "", "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            finalizer.record_origin(self.path)
            requests.append((self.path, self.headers.get("Host")))
            filename = self.path.split("?", 1)[0].rsplit("/", 1)[-1]
            path = (
                finalizer.root
                / "collected/img/incidence_maps/country"
                / filename
            )
            content = (
                b"stale"
                if behavior["stale"] in filename and behavior["stale"]
                else path.read_bytes()
            )
            self.send_response(behavior["status"])
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "variables": {
                "INFODENGUE_WEB_ORIGIN": f"http://127.0.0.1:{server.server_port}",
                "INFODENGUE_WEB_HOST": "deployment.example",
                "FINALIZER_TEST_WEB_PORT": str(server.server_port),
            },
            "requests": requests,
            "behavior": behavior,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("purge", [False, True])
def test_production_checks_real_origin_with_host_and_week(
    finalizer, origin, purge
):
    variables = dict(origin["variables"])
    if purge:
        variables.update(
            INFODENGUE_NGINX_CONTAINER="external-proxy",
            INFODENGUE_NGINX_CACHE_PATH="/cache/nginx",
        )
    result = finalizer.run(profile="prod", **variables)
    assert result.returncode == 0, result.stderr
    assert origin["requests"] == [
        (
            f"/static/img/incidence_maps/country/incidence_Nacional_{disease}.png?v=202638",
            "deployment.example",
        )
        for disease in ("dengue", "chikungunya")
    ]
    commands = finalizer.commands()
    assert "containers/compose-prod.yaml" in commands[0]["args"]
    if purge:
        assert commands[4]["args"] == [
            "exec",
            "external-proxy",
            "find",
            "/cache/nginx",
            "-type",
            "f",
            "-delete",
        ]
        validations = commands[5:]
    else:
        validations = commands[4:]
        assert (
            "external nginx cache invalidation is not configured"
            in result.stdout
        )
    assert 'MAX("SE")::integer' in validations[0]["sql"]
    assert [call["command"] for call in validations[1:]] == [
        "docker",
        "http",
        "docker",
        "http",
    ]
    assert "sha256sum" in validations[1]["args"]
    assert "sha256sum" in validations[3]["args"]


@pytest.mark.parametrize(
    "stale,status", [("dengue", 200), ("chikungunya", 200), ("", 500)]
)
def test_origin_failure_after_nginx_purge_prevents_success(
    finalizer, origin, stale, status
):
    origin["behavior"].update(stale=stale, status=status)
    result = finalizer.run(
        profile="prod",
        **origin["variables"],
        INFODENGUE_NGINX_CONTAINER="external-proxy",
        INFODENGUE_NGINX_CACHE_PATH="/cache/nginx",
    )
    assert result.returncode != 0
    assert "succeeded" not in result.stdout
    assert "find" in finalizer.commands()[4]["args"]
    if stale:
        assert "Origin map SHA256 mismatch" in result.stderr


@pytest.mark.parametrize(
    "variables",
    [
        {},
        {"INFODENGUE_WEB_ORIGIN": "http://127.0.0.1:8000"},
        {"INFODENGUE_WEB_ORIGIN": "invalid", "INFODENGUE_WEB_HOST": "example"},
        {
            "INFODENGUE_WEB_ORIGIN": "https://info.dengue.mat.br",
            "INFODENGUE_WEB_HOST": "info.dengue.mat.br",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://info.dengue.mat.br:8000",
            "INFODENGUE_WEB_HOST": "info.dengue.mat.br",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://www.info.dengue.mat.br:8000",
            "INFODENGUE_WEB_HOST": "info.dengue.mat.br",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://127.0.0.1:80",
            "INFODENGUE_WEB_HOST": "example",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://127.0.0.1:9000",
            "INFODENGUE_WEB_HOST": "example",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "https://127.0.0.1:8000",
            "INFODENGUE_WEB_HOST": "example",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://127.0.0.1:8000",
            "INFODENGUE_WEB_HOST": "example",
            "INFODENGUE_NGINX_CONTAINER": "proxy",
        },
        {
            "INFODENGUE_WEB_ORIGIN": "http://127.0.0.1:8000",
            "INFODENGUE_WEB_HOST": "example",
            "INFODENGUE_NGINX_CONTAINER": "proxy",
            "INFODENGUE_NGINX_CACHE_PATH": "/",
        },
    ],
)
def test_invalid_production_configuration_stops_before_refresh(
    finalizer, variables
):
    result = finalizer.run(profile="prod", **variables)
    assert result.returncode != 0
    assert finalizer.commands() == []


def test_rsync_failure_prevents_collectstatic_and_cache_clear(finalizer):
    result = finalizer.run(fault="rsync")
    assert result.returncode != 0
    assert len(finalizer.commands()) == 2


def test_makim_task_delegates_with_named_arguments():
    config = yaml.safe_load((ROOT / ".makim.yaml").read_text())
    task = config["groups"]["deployment"]["tasks"]["finalize-analysis"]
    assert all(
        task["args"][name]["required"]
        for name in ("env", "week", "maps-source")
    )
    assert task["run"].startswith("scripts/finalize_analysis_run.sh")
    for name in ("env", "week", "maps-source"):
        assert (
            f'--{name} "${{{{ args.{name.replace("-", "_")} }}}}"'
            in task["run"]
        )


def test_semantically_invalid_week_stops_at_read_only_validation(finalizer):
    result = finalizer.run(
        [
            "--env",
            "staging",
            "--week",
            "202654",
            "--maps-source",
            str(finalizer.maps),
        ]
    )
    assert result.returncode == 2
    assert "Invalid --week" in result.stderr
    assert finalizer.commands() == []
    checks = finalizer.all_commands()
    assert len(checks) == 1
    assert "Week.fromstring" in checks[0]["args"][-2]
    assert (finalizer.published / "obsolete.png").read_bytes() == b"old"


@pytest.mark.parametrize("redirect", ["incidence_maps", "static"])
def test_destination_escape_is_rejected_before_workflow(finalizer, redirect):
    target = (
        finalizer.published
        if redirect == "incidence_maps"
        else finalizer.root / "AlertaDengue/static"
    )
    outside = finalizer.root.parent / "unrelated-static"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("unrelated assets")
    shutil.rmtree(target)
    target.symlink_to(outside, target_is_directory=True)
    result = finalizer.run()
    assert result.returncode != 0
    assert "destination escapes" in result.stderr
    assert finalizer.all_commands() == []
    assert marker.read_text() == "unrelated assets"


def test_source_destination_overlap_is_still_rejected(finalizer):
    shutil.copytree(finalizer.maps, finalizer.published, dirs_exist_ok=True)
    result = finalizer.run(
        [
            "--env",
            "staging",
            "--week",
            "202638",
            "--maps-source",
            str(finalizer.published),
        ]
    )
    assert result.returncode != 0
    assert "Maps source must be outside" in result.stderr
    assert finalizer.all_commands() == []


def test_direct_http_origin_matches_configured_web_port(finalizer):
    # Stop at refresh, so accepting the deployment address makes no remote request.
    result = finalizer.run(
        profile="prod",
        fault="refresh",
        INFODENGUE_WEB_ORIGIN="http://65.21.204.98:8000",
        INFODENGUE_WEB_HOST="info.dengue.mat.br",
    )
    assert result.returncode == 7
    assert len(finalizer.commands()) == 1
    assert finalizer.commands()[0]["sql"].startswith("BEGIN;")


def test_cache_clear_returning_none_is_accepted(finalizer):
    from django.core.cache.backends.locmem import LocMemCache

    assert LocMemCache("finalizer-test", {}).clear() is None
    result = finalizer.run()
    assert result.returncode == 0, result.stderr
    assert (
        finalizer.commands()[3]["args"][-1]
        == "from django.core.cache import cache; cache.clear()"
    )


def test_cache_command_failure_stops_before_nginx_and_validation(
    finalizer, origin
):
    result = finalizer.run(
        profile="prod",
        fault="cache",
        **origin["variables"],
        INFODENGUE_NGINX_CONTAINER="proxy",
        INFODENGUE_NGINX_CACHE_PATH="/cache/nginx",
    )
    assert result.returncode == 9
    assert len(finalizer.commands()) == 4
    assert origin["requests"] == []


def test_nginx_failure_stops_before_postcondition_validation(
    finalizer, origin
):
    result = finalizer.run(
        profile="prod",
        fault="nginx",
        **origin["variables"],
        INFODENGUE_NGINX_CONTAINER="proxy",
        INFODENGUE_NGINX_CACHE_PATH="/cache/nginx",
    )
    assert result.returncode == 10
    assert len(finalizer.commands()) == 5
    assert origin["requests"] == []
