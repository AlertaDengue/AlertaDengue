# Contributing to InfoDengue

Thank you for contributing to InfoDengue.

This guide describes the recommended workflow for setting up the AlertaDengue development environment, running tests, documenting changes, and submitting pull requests.

## Prerequisites

Install the following tools:

- Git
- Docker
- Miniforge or Mambaforge
- UV
- Poetry
- Makim
- containers-sugar

## Repository setup

Fork and clone the repository:

```bash
git clone git@github.com:<your-user>/AlertaDengue.git
cd AlertaDengue
````

Add the upstream remote:

```bash
git remote add upstream git@github.com:AlertaDengue/AlertaDengue.git
git fetch --all
```

Some development workflows may also require the demo data repository:

```bash
git clone git@github.com:AlertaDengue/Data.git
```

Follow the `Data` repository documentation when working with demo databases or local test data.

## Development environment

Create the development environment:

```bash
mamba env create -f conda/environment.yaml
```

Activate it:

```bash
mamba activate alertadengue-dev
```

If the environment already exists, update it with:

```bash
mamba env update -f conda/environment.yaml --prune
```

Install project dependencies:

```bash
bash scripts/install-deps.sh
```

This script is the preferred dependency installation entry point. It keeps the local environment aligned with the project dependency workflow using UV and Poetry.

Validate the environment:

```bash
python AlertaDengue/manage.py check
```

## Environment configuration

Runtime configuration is loaded from:

```text
.envs/.env
```

Create this file according to the environment you are working with and review it before starting services. Required values must be defined for the application and containers to start correctly.

Do not commit local `.env` files, credentials, secrets, or machine-specific paths.

## Services

The project uses `containers-sugar` to manage services.

Available profiles are defined in `sugar.yaml`:

* `dev`
* `staging`
* `prod`

For local development, use the `dev` profile.

Start services:

```bash
sugar --profile dev compose-ext start -- -d
```

Check service status:

```bash
sugar --profile dev compose-ext ps
```

Restart services:

```bash
sugar --profile dev compose-ext restart -- -d
```

Stop services:

```bash
sugar --profile dev compose-ext stop
```

Restart selected services:

```bash
sugar --profile dev compose-ext restart \
  --services postgres rabbitmq redis memcached web celery celery-beat \
  -- -d
```

Use `sugar` instead of raw Compose commands so local and deployed workflows remain consistent.

## Database

Apply migrations:

```bash
python AlertaDengue/manage.py migrate
```

Create migrations after changing Django models:

```bash
python AlertaDengue/manage.py makemigrations
```

Create a superuser when needed:

```bash
python AlertaDengue/manage.py createsuperuser
```

Include migrations when model changes require them. Avoid committing unrelated migrations.

## Tests

The project exposes test tasks through Makim.

Prepare the test environment:

```bash
makim tests.setup
```

Run unit tests:

```bash
makim tests.unit
```

Run lint checks:

```bash
makim tests.lint
```

Clean up the test environment when needed:

```bash
makim tests.teardown
```

Pull requests are also validated by CI. Before requesting review, run the relevant local Makim checks and make sure CI passes.

## Code style

Follow standard Python open-source practices:

* keep pull requests focused;
* prefer readable and explicit code;
* add or update tests for behavior changes;
* update documentation when setup, operations, APIs, or user-facing behavior changes;
* avoid unrelated formatting changes;
* avoid committing secrets, logs, cache files, local paths, or temporary files;
* use type hints when they improve clarity;
* keep Django management commands and Celery tasks idempotent where possible;
* make operational failures explicit through clear logging.

For ingestion and data-processing code, prioritize correctness, reproducibility, and recoverability.

## Documentation

Documentation lives under:

```text
docs/
```

Use focused documents instead of large mixed-purpose files.

Current documentation areas include:

```text
docs/api/
docs/ingestion/
docs/pgbackrest/
```

The internal notification API documentation is available at:

```text
docs/api/internal_notification_api.md
```

Use it when working with notification API endpoints, payloads, authentication, or integration behavior.

The SINAN ingestion documentation is available under:

```text
docs/ingestion/
```

It covers ingestion architecture, canonical storage layout, operational commands, and recovery procedures.

The pgBackRest documentation is available at:

```text
docs/pgbackrest/README.md
```

Use it when working with PostgreSQL backup, restore, validation, or scheduled backup workflows.

Operational documentation should prefer Makim and containers-sugar commands. Do not add legacy `make` commands.

## Dependency updates

When changing dependencies:

1. Update the appropriate dependency files.
2. Run the project dependency installer:

```bash
bash scripts/install-deps.sh
```

3. Run the relevant checks and tests.
4. Mention the dependency change in the pull request description.

Keep dependency-only changes isolated when possible, especially for major upgrades.

## Git workflow

Create a branch from the latest upstream branch:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b <short-description>
```

Use clear commit messages:

```text
type(scope): short description
```

Examples:

```text
docs(api): update internal notification API guide
docs(ingestion): add SINAN recovery guide
fix(api): validate notification payload fields
test(ingestion): cover requeue behavior
refactor(tasks): simplify ingestion retry flow
ci(tests): update unit test workflow
```

Common commit types:

* `feat`
* `fix`
* `docs`
* `test`
* `refactor`
* `chore`
* `ci`

Push your branch:

```bash
git push origin <short-description>
```

Then open a pull request against the upstream repository.

## Pull requests

A pull request should explain:

* what changed;
* why the change is needed;
* how it was tested;
* whether it affects migrations, deployment, ingestion, Celery, scheduled tasks, dependencies, documentation, APIs, or backup/restore workflows.

Before requesting review, check that:

* the branch is up to date with upstream;
* the change is focused;
* tests and lint checks pass locally when relevant;
* CI passes;
* documentation was updated when needed;
* migrations are included when required;
* no secrets, logs, local paths, or temporary files were committed.

## Releases

Releases should be prepared from a clean, tested branch.

Before preparing a release, confirm that:

* CI is passing;
* migrations are reviewed;
* dependency changes are understood;
* documentation is updated;
* operational changes are documented;
* release notes or changelog entries are prepared when required.

Release pull requests should clearly identify:

* user-facing changes;
* database migrations;
* dependency updates;
* deployment changes;
* API changes;
* ingestion, Celery, or scheduled-task changes;
* backup and restore implications, when relevant;
* rollback considerations, when relevant.

Avoid mixing unrelated refactors into release preparation.
