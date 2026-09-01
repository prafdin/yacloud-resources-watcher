# Administrator Guide

## Prerequisites

- Docker and Docker Compose installed
- Yandex Cloud account with billing enabled
- Telegram account
- Basic command line knowledge

## Yandex Cloud Setup

### 1. Create Service Account

```bash
# Create service account
yc iam service-account create --name bot-watcher

# Get service account ID
SA_ID=$(yc iam service-account get --name bot-watcher --format json | jq -r .id)
echo "Service Account ID: $SA_ID"
```

### 2. Assign Viewer Role

```bash
# Get folder ID
FOLDER_ID=$(yc config get folder-id)
echo "Folder ID: $FOLDER_ID"

# Assign viewer role (read-only access)
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role viewer \
  --subject serviceAccount:$SA_ID

# Verify role assignment
yc resource-manager folder list-access-bindings $FOLDER_ID --format json | jq '.[] | select(.role_id == "viewer")'
```

### 3. Create Authorized Key

```bash
# Create authorized key and save to config directory
yc iam key create \
  --service-account-name bot-watcher \
  --output config/sa-key.json

# Verify key file
cat config/sa-key.json | jq .
```

**Important:** Keep `sa-key.json` secure and never commit it to git!

### 4. Get Folder and Cloud IDs

```bash
# Get folder ID
FOLDER_ID=$(yc config get folder-id)
echo "Folder ID: $FOLDER_ID"

# Get cloud ID
CLOUD_ID=$(yc config get cloud-id)
echo "Cloud ID: $CLOUD_ID"
```

## Telegram Bot Setup

### 1. Create Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow instructions:
   - Enter bot name (e.g., "My Cloud Watcher")
   - Enter bot username (e.g., "my_cloud_watcher_bot")
4. Save the bot token (format: `1234567890:ABCdef...`)

### 2. Get Your User ID

1. Open Telegram and search for `@userinfobot`
2. Send any message
3. Save your user ID (numeric value)

## Installation

### Option 1: Using Install Script (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd yacloud-resources-watcher

# Run installation script
./scripts/install.sh

# Follow prompts to configure
```

### Option 2: Manual Installation

```bash
# Create directories
mkdir -p config

# Copy config files
cp config.yaml.example config/config.yaml
cp .env.example .env

# Edit .env
nano .env
# Set TELEGRAM_BOT_TOKEN

# Edit config/config.yaml
nano config/config.yaml
# Set:
# - telegram.allowed_user_id
# - yandex_cloud.folder_id
# - yandex_cloud.cloud_id
# - scheduler.timezone (if needed)

# Place SA key
cp /path/to/sa-key.json config/sa-key.json

# Build and start
docker compose -f docker/docker-compose.yml up -d --build
```

## Configuration

### .env File

```bash
# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Timezone
TZ=Europe/Moscow
```

### config/config.yaml File

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  allowed_user_id: 123456789  # Your Telegram user ID

scheduler:
  daily_report_time: "21:00"  # HH:MM format
  timezone: "Europe/Moscow"   # IANA timezone
  reminder_hours: 2           # Hours before reminder

yandex_cloud:
  folder_id: "b1g..."         # From yc config get folder-id
  cloud_id: "b1g..."          # From yc config get cloud-id
  service_account_key_path: "/app/config/sa-key.json"

storage:
  database_path: "/app/data/bot.db"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `telegram.bot_token` | Telegram bot token | Required |
| `telegram.allowed_user_id` | Authorized user ID | Required |
| `scheduler.daily_report_time` | Daily report time (HH:MM) | "21:00" |
| `scheduler.timezone` | Timezone (IANA format) | "Europe/Moscow" |
| `scheduler.reminder_hours` | Hours before reminder | 2 |
| `yandex_cloud.folder_id` | YC folder ID | Required |
| `yandex_cloud.cloud_id` | YC cloud ID | Required |
| `yandex_cloud.service_account_key_path` | Path to SA key | "/app/config/sa-key.json" |
| `storage.database_path` | SQLite database path | "/app/data/bot.db" |
| `logging.level` | Log level | "INFO" |

## Starting the Bot

```bash
# Start bot
docker compose -f docker/docker-compose.yml up -d

# Check status
docker compose -f docker/docker-compose.yml ps

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Stop bot
docker compose -f docker/docker-compose.yml down
```

## Updating the Bot

### Using Update Script

```bash
./scripts/update.sh
```

### Manual Update

```bash
# Backup database from Docker named volume
docker compose -f docker/docker-compose.yml cp \
  yc-watcher-bot:/app/data/bot.db backup_$(date +%Y%m%d)/bot.db

# Pull changes
git pull origin main

# Rebuild and restart
docker compose -f docker/docker-compose.yml up -d --build
```

## Monitoring

### View Logs

```bash
# Real-time logs
docker compose -f docker/docker-compose.yml logs -f

# Last 100 lines
docker compose -f docker/docker-compose.yml logs --tail=100

# Filter by level
docker compose -f docker/docker-compose.yml logs | grep ERROR
```

### Check Health

```bash
# Container status
docker compose -f docker/docker-compose.yml ps

# Health check
docker inspect --format='{{.State.Health.Status}}' yc-watcher-bot
```

### Database Inspection

```bash
# Enter container
docker exec -it yc-watcher-bot sh

# Use SQLite
sqlite3 /app/data/bot.db

# Query examples
SELECT * FROM pending_notifications WHERE acknowledged = 0;
SELECT COUNT(*) FROM notification_history;
```

## Troubleshooting

### Bot Not Responding

**Symptoms:** Bot doesn't respond to commands

**Solutions:**
1. Check bot is running: `docker compose ps`
2. Check logs: `docker compose logs -f`
3. Verify bot token in `.env`
4. Verify user ID in `config/config.yaml`
5. Restart bot: `docker compose restart`

### YC API Errors

**Symptoms:** "Failed to fetch resources" or empty resource list

**Solutions:**
1. Verify SA key exists: `ls -la config/sa-key.json`
2. Verify SA key is valid: `cat config/sa-key.json | jq .`
3. Check SA has viewer role: `yc resource-manager folder list-access-bindings <folder-id>`
4. Verify folder_id and cloud_id in config
5. Check folder has resources: `yc compute instance list`

### Authentication Errors

**Symptoms:** "Unauthorized" or "Invalid JWT" errors

**Solutions:**
1. Regenerate SA key:
   ```bash
   yc iam key delete --id <key-id>
   yc iam key create --service-account-name bot-watcher --output config/sa-key.json
   ```
2. Restart bot to load new key
3. Check system time is correct (JWT is time-sensitive)

### Database Errors

**Symptoms:** Database lock or corruption

**Solutions:**
1. Stop bot: `docker compose down`
2. Backup current DB: `docker compose -f docker/docker-compose.yml cp yc-watcher-bot:/app/data/bot.db ./bot.db.backup`
3. Reset database: `docker compose -f docker/docker-compose.yml run --rm bot rm /app/data/bot.db` (or `docker volume rm` for full reset)
4. Start bot: `docker compose up -d`

### Permission Denied

**Symptoms:** "Permission denied" when accessing files

**Solutions:**
1. Check Docker user: `docker exec yc-watcher-bot whoami`
2. Verify named volume works: `docker compose ls`
3. Data is stored in a Docker named volume `bot_data`, not on the host filesystem

### No Resources Shown

**Symptoms:** Report shows 0 resources

**Solutions:**
1. Verify folder has resources: `yc compute instance list --folder-id <folder-id>`
2. Check SA has access to folder
3. Enable debug logging: set `logging.level: "DEBUG"` in config
4. Check logs for API errors

## Backup and Restore

### Backup

```bash
BACKUP_DIR=backup_$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# Backup database from Docker named volume
docker compose -f docker/docker-compose.yml cp \
  yc-watcher-bot:/app/data/bot.db $BACKUP_DIR/bot.db

# Backup config
cp config/config.yaml $BACKUP_DIR/

# Backup SA key (store securely!)
cp config/sa-key.json $BACKUP_DIR/
```

### Restore

```bash
# Start bot (named volume bot_data is created automatically)
docker compose -f docker/docker-compose.yml up -d

# Restore database into named volume
docker compose -f docker/docker-compose.yml cp \
  backup_20240115/bot.db yc-watcher-bot:/app/data/bot.db

# Restore config (if needed)
cp backup_20240115/config.yaml config/config.yaml

# Restart bot
docker compose -f docker/docker-compose.yml restart
```

## Security Best Practices

### Yandex Cloud

1. **Use viewer role only** - Never assign editor or admin roles
2. **Rotate SA keys periodically** - Delete old keys, create new ones
3. **Monitor API access** - Check YC audit logs
4. **Use separate folder** - Isolate bot access to specific folder

### Telegram

1. **Keep bot token secret** - Never share or commit to git
2. **Use single user ID** - Don't share bot access
3. **Monitor unauthorized access** - Check logs for denied attempts

### Docker

1. **Run as non-root** - Already configured in Dockerfile
2. **Read-only mounts** - Config files mounted as read-only
3. **Resource limits** - CPU and memory limits configured
4. **No privileged mode** - Don't enable privileged mode

### General

1. **Keep secrets out of git** - Use .gitignore
2. **Regular updates** - Keep dependencies updated
3. **Monitor logs** - Check for errors and unauthorized access
4. **Backup regularly** - Automate backups of data and config

## Maintenance

### Log Rotation

Docker automatically rotates logs (configured in docker-compose.yml):
- Max size: 10MB per file
- Max files: 3

### Database Cleanup

Old notifications are kept for history. To cleanup manually:

```bash
docker exec -it yc-watcher-bot sh
sqlite3 /app/data/bot.db
DELETE FROM notification_history WHERE sent_at < datetime('now', '-90 days');
.quit
```

### Dependency Updates

```bash
# Update requirements.txt
pip install -U -r requirements.txt
pip freeze > requirements.txt

# Rebuild Docker image
docker compose -f docker/docker-compose.yml up -d --build
```

## Support

For issues and questions:
1. Check logs: `docker compose logs -f`
2. Review documentation: README.md, docs/USER.md
3. Check technical specification: docs/SPEC.md
4. Review architecture: docs/ARCHITECTURE.md
