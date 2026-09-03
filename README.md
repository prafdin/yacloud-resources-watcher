# Yandex Cloud Resources Watcher

A single-purpose Telegram bot. Once a day at a configured time it posts a
point-in-time inventory of the resources that currently exist in one Yandex
Cloud folder, grouped by type. It also answers `/resources` on demand.

No diffing, no database, no acknowledgement flow — just "what is in the folder
right now".

## Reported resource types

Compute instances, disks, VPC networks, VPC subnets, Object Storage buckets,
Managed PostgreSQL / MySQL / ClickHouse / MongoDB clusters, serverless
functions, serverless containers.

A resource type that fails to list (for example a missing IAM role) is shown as
a failed section; the rest of the report is still delivered.

## Commands

| Command | Effect |
|---|---|
| `/start` | Liveness reply |
| `/resources` | Build and send the inventory now |

Only Telegram user IDs in `TELEGRAM_ALLOWED_USER_IDS` are answered. The daily
report is sent to `TELEGRAM_CHAT_ID`.

## Configuration

All configuration is via environment variables (a `.env` file is read if
present). See `.env.example`.

| Variable | Meaning |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | Comma-separated Telegram user IDs allowed to use commands |
| `TELEGRAM_CHAT_ID` | Chat that receives the scheduled report |
| `YC_SA_KEY_FILE` | Path to a Yandex Cloud service-account key JSON |
| `YC_FOLDER_ID` | Folder to scan |
| `SCHEDULE_TIME` | Daily report time, `HH:MM` |
| `SCHEDULE_TIMEZONE` | IANA timezone for `SCHEDULE_TIME`, e.g. `Europe/Amsterdam` |
| `LOG_LEVEL` | Root log level, default `INFO` |

The service account needs `viewer` on the folder (or per-service viewer roles).

## Run locally

```
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # then edit it
yc iam key create --service-account-name <sa> --output sa-key.json
python -m yc_watcher
```

## Run with Docker

```
cp .env.example .env          # then edit it; keep YC_SA_KEY_FILE=/secrets/sa-key.json
# put the service-account key at ./sa-key.json
docker compose up --build -d
```

## Tests

```
pip install -e ".[dev]"
python -m pytest
```

All external I/O is mocked; the suite needs no network and no credentials.

## Deploy

Pushing a `vX.Y.Z` git tag runs `.github/workflows/deploy.yml`: it builds the
image, pushes it to `ghcr.io/prafdin/yacloud-resources-watcher`, then SSHes into
the server and runs `docker compose pull && up -d` in `~/yc-watcher`. The app is
stateless, so an update is just a container restart.

```
# version lives in pyproject.toml
git tag v0.1.0 && git push origin v0.1.0
```

**Rollback** (image tags persist in GHCR):

```
ssh <user>@<host> "cd yc-watcher && APP_VERSION=v0.1.0 docker compose up -d"
```

### One-time setup

Repo **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `DEPLOY_SSH_HOST` | server IP / hostname |
| `DEPLOY_SSH_USER` | SSH login |
| `DEPLOY_SSH_KEY` | deploy private key, including the `BEGIN`/`END` lines |

On the server:

1. Install Docker Engine + the Compose v2 plugin; add the deploy user to the
   `docker` group and re-login.
2. `mkdir -p ~/yc-watcher`, then place `~/yc-watcher/.env` and
   `~/yc-watcher/sa-key.json` (see `.env.example`).
3. Add the deploy key's public half to `~/.ssh/authorized_keys`; open inbound TCP 22.

After the first `build-and-push`, set the GHCR package visibility to **Public**
(repo → Packages → package settings), then re-run the `deploy` job.
