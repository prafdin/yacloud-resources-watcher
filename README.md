# Yandex Cloud Resources Watcher Bot

Telegram bot for monitoring Yandex Cloud resources with scheduled notifications and on-demand reporting.

## Features

- 📊 **Daily Reports**: Receive resource reports at configurable time (default: 21:00)
- ⏰ **Smart Reminders**: Automatic reminder if you don't acknowledge with "OK"
- 🔍 **On-Demand**: Request current resource status anytime with `/resources`
- 🔒 **Secure**: Single-user access control, least privilege YC permissions
- 🐳 **Docker Ready**: Easy deployment with Docker Compose
- 📦 **Comprehensive**: Monitors all Yandex Cloud resource types

## Monitored Resources

- Compute Instances (VMs)
- Managed Databases (PostgreSQL, MySQL, MongoDB, ClickHouse)
- Object Storage Buckets
- VPC Networks, Subnets, Security Groups
- Load Balancers
- Container Registries
- Serverless Functions and Containers
- DNS Zones
- API Gateways

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Yandex Cloud account with billing enabled
- Telegram account

### Installation

```bash
# Clone repository
git clone <repository-url>
cd yacloud-resources-watcher

# Run installation script
./scripts/install.sh
```

### Manual Installation

```bash
# Create directories
mkdir -p config data

# Copy config files
cp config.yaml.example config/config.yaml
cp .env.example .env

# Edit configuration
nano .env
nano config/config.yaml

# Create Service Account in Yandex Cloud
yc iam service-account create --name bot-watcher

# Assign viewer role
FOLDER_ID=$(yc config get folder-id)
SA_ID=$(yc iam service-account get --name bot-watcher --format json | jq -r .id)
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role viewer \
  --subject serviceAccount:$SA_ID

# Create authorized key
yc iam key create \
  --service-account-name bot-watcher \
  --output config/sa-key.json

# Build and start
docker compose -f docker/docker-compose.yml up -d --build
```

## Configuration

### .env

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TZ=Europe/Moscow
```

### config/config.yaml

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  allowed_user_id: 123456789  # Your Telegram user ID

scheduler:
  daily_report_time: "21:00"
  timezone: "Europe/Moscow"
  reminder_hours: 2

yandex_cloud:
  folder_id: "b1g..."
  cloud_id: "b1g..."
  service_account_key_path: "/app/config/sa-key.json"
```

## Usage

### Bot Commands

- `/start` - Welcome message and setup
- `/resources` - Get current resource list
- `/status` - Check bot and scheduler status
- `/help` - Show help message

### Daily Reports

1. Bot sends resource report at configured time (default: 21:00)
2. Review the report
3. Reply "OK" to acknowledge
4. If no acknowledgment within 2 hours, bot sends reminder

### Example Report

```
📊 Yandex Cloud Resources Report

🖥️ Compute Instances (2):
  • vm-1: RUNNING (CPU: 2, RAM: 4GB, IP: 51.250.1.1)
  • vm-2: STOPPED

🗄️ Databases (1):
  • postgres-cluster: RUNNING (v15, s2.micro)

📦 Storage Buckets (2):
  • my-bucket-1
  • my-bucket-2

Total: 5 resources (3 running, 1 stopped, 1 other)

Reply OK to acknowledge
```

## Updating

```bash
./scripts/update.sh
```

Or manually:

```bash
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d --build
```

## Documentation

- [Administrator Guide](docs/ADMIN.md) - Detailed setup and troubleshooting
- [User Guide](docs/USER.md) - How to use the bot
- [Technical Specification](docs/SPEC.md) - Complete technical specification
- [Architecture](docs/ARCHITECTURE.md) - System architecture and design

## Security

### Yandex Cloud

- Service Account has only `viewer` role (read-only)
- No write permissions to cloud resources
- Authorized key stored securely

### Telegram

- Bot responds only to authorized user ID
- Unauthorized access attempts are logged
- No sensitive data in messages

### Docker

- Runs as non-root user
- Config files mounted as read-only
- Resource limits configured
- No privileged mode

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Project Structure

```
yacloud-resources-watcher/
├── bot/                    # Telegram bot logic
├── yandex_cloud/           # YC API client
├── storage/                # Database operations
├── config/                 # Configuration
├── tests/                  # Unit tests
├── scripts/                # Installation scripts
├── docker/                 # Docker files
└── docs/                   # Documentation
```

## Troubleshooting

### Bot not responding
- Check logs: `docker compose -f docker/docker-compose.yml logs -f`
- Verify bot token in `.env`
- Check user ID in `config/config.yaml`

### YC API errors
- Verify SA key is valid: `config/sa-key.json`
- Check SA has `viewer` role
- Verify folder_id and cloud_id

### No resources shown
- Check folder has resources
- Verify SA has access to folder
- Check logs for API errors

## License

MIT

## Contributing

This is a personal project. For issues and suggestions, please open an issue in the repository.
