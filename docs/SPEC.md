# Yandex Cloud Resources Watcher Bot - Technical Specification

## 1. OVERVIEW

### 1.1 Project Purpose
Telegram bot for monitoring Yandex Cloud resources with scheduled notifications and on-demand resource reporting.

### 1.2 Target Audience
Personal bot for single user (owner/administrator).

### 1.3 Key Requirements
- **Scheduled Notifications**: Daily resource report at configurable time (default: 21:00)
- **Reminder System**: Re-send report after 2 hours if user doesn't acknowledge with "OK"
- **On-Demand Reports**: User can request current resource status via `/resources` command
- **Access Control**: Bot responds only to authorized Telegram user
- **Security**: Least privilege access to Yandex Cloud (read-only)
- **Deployment**: Docker-based deployment with installation/update scripts
- **Testing**: Unit tests with 80%+ coverage

### 1.4 User Stories
1. As a user, I want to receive daily notifications at 21:00 with information about all created and running resources in my Yandex Cloud project
2. As a user, I want the bot to repeat the message after 2 hours if I didn't reply "OK" to the previous message
3. As a user, I want to request current resource information via `/resources` command
4. As an administrator, I want to install and update the application using Docker
5. As an administrator, I want installation and update guides
6. As an administrator, I want installation and update scripts
7. As an administrator, I want to secure my cloud project using least privilege access
8. As an administrator, I want the bot to be controlled only by a specific Telegram user
9. As a developer, I want unit tests to prevent breaking the application during updates

---

## 2. ARCHITECTURE

### 2.1 Project Structure
```
yacloud-resources-watcher/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Entry point, bot initialization
│   ├── handlers.py          # Command handlers (/start, /resources, /status, /help)
│   ├── scheduler.py         # APScheduler setup and job definitions
│   └── middleware.py        # Access control middleware
├── yandex_cloud/
│   ├── __init__.py
│   ├── client.py            # YC REST API client
│   ├── resources.py         # Resource fetching logic for all resource types
│   └── auth.py              # Service Account authentication, IAM token management
├── storage/
│   ├── __init__.py
│   ├── database.py          # SQLite connection and operations
│   └── models.py            # Data models for notifications
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration loading and validation
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_handlers.py     # Bot handler tests
│   ├── test_resources.py    # YC resource fetching tests
│   ├── test_scheduler.py    # Scheduler logic tests
│   └── test_auth.py         # Authentication tests
├── scripts/
│   ├── install.sh           # Installation script
│   └── update.sh            # Update script
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   ├── SPEC.md              # This file
│   ├── ADMIN.md             # Administrator guide
│   └── USER.md              # User guide
├── README.md
├── AGENTS.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── config.yaml.example
└── .gitignore
```

### 2.2 Component Responsibilities

#### bot/main.py
- Initialize aiogram Bot and Dispatcher
- Load configuration
- Setup scheduler
- Initialize database
- Start polling

#### bot/handlers.py
- `/start` - Welcome message, access check
- `/resources` - Fetch and send current resource list
- `/status` - Bot and scheduler status
- `/help` - Command list and usage
- Text message handler for "OK" acknowledgment

#### bot/scheduler.py
- Setup APScheduler with AsyncIOScheduler
- Add daily report job (configurable time)
- Add reminder check job (runs every 30 minutes)
- Handle timezone configuration

#### bot/middleware.py
- Check if message.from_user.id matches config.telegram.allowed_user_id
- Reject unauthorized users with "Access denied" message
- Log unauthorized access attempts

#### yandex_cloud/auth.py
- Load Service Account key from JSON file
- Generate JWT token (signed with private key)
- Exchange JWT for IAM token via YC IAM API
- Cache IAM token, refresh before expiry (IAM tokens valid for 12 hours)

#### yandex_cloud/client.py
- HTTP client using aiohttp
- Methods for each YC API endpoint
- Error handling and retry logic
- Rate limiting support

#### yandex_cloud/resources.py
- Fetch all resource types:
  - Compute instances
  - Managed databases (PostgreSQL, MySQL, MongoDB, ClickHouse)
  - Object Storage buckets
  - VPC resources (networks, subnets, security groups)
  - Load balancers
  - Container registries
  - Serverless functions
  - DNS zones
  - API Gateways
- Format resource data into report message

#### storage/database.py
- SQLite connection management
- CRUD operations for pending_notifications table
- CRUD operations for notification_history table
- Async operations using aiosqlite

#### storage/models.py
- Pydantic models for data validation
- Notification model
- Resource models

#### config/settings.py
- Load config.yaml
- Load .env variables
- Validate configuration using Pydantic
- Provide typed configuration object

---

## 3. TECHNOLOGY STACK

### 3.1 Core Dependencies
```
aiogram==3.3.0          # Telegram bot framework (async)
aiohttp==3.9.1          # Async HTTP client for YC REST API
apscheduler==3.10.4     # Task scheduling (AsyncIOScheduler)
aiosqlite==0.19.0       # Async SQLite driver
pydantic==2.5.2         # Configuration and data validation
pyyaml==6.0.1           # YAML configuration parsing
python-dotenv==1.0.0    # Environment variable loading
PyJWT==2.8.0            # JWT token generation for YC auth
cryptography==41.0.7    # RSA key handling for JWT signing
```

### 3.2 Development Dependencies
```
pytest==7.4.3           # Testing framework
pytest-asyncio==0.23.2  # Async test support
pytest-mock==3.12.0     # Mocking support
pytest-cov==4.1.0       # Coverage reporting
aioresponses==0.7.6     # Mock aiohttp requests
black==23.12.1          # Code formatting
ruff==0.1.9             # Linting
mypy==1.8.0             # Type checking
```

### 3.3 Justification
- **aiogram**: Modern async framework, better performance than python-telegram-bot
- **aiohttp**: Native async HTTP client, works well with aiogram
- **apscheduler**: Mature scheduling library with async support
- **aiosqlite**: Async SQLite, no external database needed for simple state tracking
- **pydantic**: Type-safe configuration, validation, serialization
- **SQLite**: Simple, file-based, no separate service required

---

## 4. YANDEX CLOUD INTEGRATION

### 4.1 Authentication Flow

```
1. Load Service Account authorized key from JSON file
   - Contains: id, service_account_id, private_key, public_key
   
2. Generate JWT token
   - Header: {"alg": "PS256", "typ": "JWT", "kid": "<key_id>"}
   - Payload: {
       "iss": "<service_account_id>",
       "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
       "iat": <current_timestamp>,
       "exp": <current_timestamp + 3600>
     }
   - Sign with private key using PS256 algorithm
   
3. Exchange JWT for IAM token
   POST https://iam.api.cloud.yandex.net/iam/v1/tokens
   Body: {"jwt": "<jwt_token>"}
   Response: {"iamToken": "<iam_token>"}
   
4. Cache IAM token
   - Store in memory with expiry time
   - Refresh 1 hour before expiry (IAM tokens valid for 12 hours)
   
5. Use IAM token for API calls
   Header: Authorization: Bearer <iam_token>
```

### 4.2 Resource API Endpoints

#### 4.2.1 Compute Instances
```
Endpoint: GET https://compute.api.cloud.yandex.net/compute/v1/instances
Query params: folderId=<folder_id>
Headers: Authorization: Bearer <iam_token>

Response:
{
  "instances": [
    {
      "id": "fhm...",
      "name": "vm-1",
      "status": "RUNNING",  # RUNNING, STOPPED, STARTING, STOPPING, ERROR
      "zoneId": "ru-central1-a",
      "resources": {
        "cores": 2,
        "memory": 4294967296,  # bytes
        "coreFraction": 100
      },
      "networkInterfaces": [
        {
          "primaryV4Address": {
            "address": "10.0.0.1",
            "oneToOneNat": {
              "address": "51.250.1.1"
            }
          }
        }
      ],
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.2 Managed PostgreSQL Clusters
```
Endpoint: GET https://mdb.api.cloud.yandex.net/managed-postgresql/v1/clusters
Query params: folderId=<folder_id>

Response:
{
  "clusters": [
    {
      "id": "c9q...",
      "name": "postgres-cluster",
      "status": "RUNNING",  # RUNNING, STOPPED, CREATING, UPDATING, DELETING
      "config": {
        "version": "15",
        "resources": {
          "resourcePresetId": "s2.micro",  # s2.micro, s2.small, etc.
          "diskSize": 10737418240,  # bytes
          "diskTypeId": "network-ssd"
        }
      },
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.3 Managed MySQL Clusters
```
Endpoint: GET https://mdb.api.cloud.yandex.net/managed-mysql/v1/clusters
Query params: folderId=<folder_id>

Response: Same structure as PostgreSQL
```

#### 4.2.4 Managed MongoDB Clusters
```
Endpoint: GET https://mdb.api.cloud.yandex.net/managed-mongodb/v1/clusters
Query params: folderId=<folder_id>

Response: Same structure as PostgreSQL
```

#### 4.2.5 Managed ClickHouse Clusters
```
Endpoint: GET https://mdb.api.cloud.yandex.net/managed-clickhouse/v1/clusters
Query params: folderId=<folder_id>

Response: Same structure as PostgreSQL
```

#### 4.2.6 Object Storage Buckets
```
Endpoint: GET https://storage.api.cloud.yandex.net/storage/v1/buckets
Query params: folderId=<folder_id>

Response:
{
  "buckets": [
    {
      "name": "my-bucket",
      "region": "ru-central1",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.7 VPC Networks
```
Endpoint: GET https://vpc.api.cloud.yandex.net/vpc/v1/networks
Query params: folderId=<folder_id>

Response:
{
  "networks": [
    {
      "id": "enp...",
      "name": "default-network",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.8 VPC Subnets
```
Endpoint: GET https://vpc.api.cloud.yandex.net/vpc/v1/subnets
Query params: folderId=<folder_id>

Response:
{
  "subnets": [
    {
      "id": "e9b...",
      "name": "default-subnet-a",
      "networkId": "enp...",
      "zoneId": "ru-central1-a",
      "v4CidrBlocks": ["10.0.0.0/24"],
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.9 VPC Security Groups
```
Endpoint: GET https://vpc.api.cloud.yandex.net/vpc/v1/securityGroups
Query params: folderId=<folder_id>

Response:
{
  "securityGroups": [
    {
      "id": "enp...",
      "name": "default-security-group",
      "networkId": "enp...",
      "rulesCount": 5,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.10 Network Load Balancers
```
Endpoint: GET https://load-balancer.api.cloud.yandex.net/load-balancer/v1/networkLoadBalancers
Query params: folderId=<folder_id>

Response:
{
  "networkLoadBalancers": [
    {
      "id": "enp...",
      "name": "my-load-balancer",
      "status": "ACTIVE",  # ACTIVE, INACTIVE, CREATING, DELETING
      "type": "EXTERNAL",
      "listeners": [
        {
          "name": "listener-1",
          "port": 80,
          "protocol": "TCP",
          "address": "51.250.1.1"
        }
      ],
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.11 Container Registries
```
Endpoint: GET https://container-registry.api.cloud.yandex.net/container-registry/v1/registries
Query params: folderId=<folder_id>

Response:
{
  "registries": [
    {
      "id": "crap...",
      "name": "my-registry",
      "status": "ACTIVE",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.12 Serverless Functions
```
Endpoint: GET https://serverless-functions.api.cloud.yandex.net/functions/v1/functions
Query params: folderId=<folder_id>

Response:
{
  "functions": [
    {
      "id": "b1g...",
      "name": "my-function",
      "status": "ACTIVE",
      "runtime": "python311",
      "timeout": "5",
      "memory": 128,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.13 Serverless Containers
```
Endpoint: GET https://containers.api.cloud.yandex.net/containers/v1/containers
Query params: folderId=<folder_id>

Response:
{
  "containers": [
    {
      "id": "b1g...",
      "name": "my-container",
      "status": "REVISION_ACTIVE",
      "memory": 128,
      "cores": 1,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.14 DNS Zones
```
Endpoint: GET https://dns.api.cloud.yandex.net/dns/v1/zones
Query params: folderId=<folder_id>

Response:
{
  "dnsZones": [
    {
      "id": "dns...",
      "name": "my-zone",
      "zone": "example.com.",
      "publicVisibility": true,
      "privateVisibility": false,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 4.2.15 API Gateways
```
Endpoint: GET https://apigateway.api.cloud.yandex.net/apigateway/v1/apigateways
Query params: folderId=<folder_id>

Response:
{
  "apiGateways": [
    {
      "id": "b1g...",
      "name": "my-api-gateway",
      "status": "ACTIVE",
      "domain": "b1g...apigw.yandexcloud.net",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 4.3 Error Handling

```python
# HTTP Status Codes
401 Unauthorized  -> Refresh IAM token and retry
403 Forbidden     -> Log error, notify user about permissions issue
404 Not Found     -> Return empty list (resource type not enabled)
429 Too Many Requests -> Wait and retry with exponential backoff
500+ Server Error -> Retry up to 3 times with backoff

# Network Errors
ConnectionError   -> Retry up to 3 times
Timeout           -> Retry up to 3 times
```

### 4.4 Rate Limiting
- YC API has rate limits (varies by service)
- Implement exponential backoff for retries
- Cache responses for short periods (5 minutes) if needed

---

## 5. TELEGRAM BOT SPECIFICATION

### 5.1 Commands

#### /start
```
Behavior:
1. Check if user is authorized (user_id matches config)
2. If authorized: Send welcome message
3. If not authorized: Send "Access denied" and log attempt

Welcome Message:
"👋 Welcome to Yandex Cloud Resources Watcher!

I'll send you daily reports about your cloud resources.

Commands:
/resources - Get current resource list
/status - Check bot status
/help - Show this help message"
```

#### /resources
```
Behavior:
1. Check authorization
2. Fetch all resources from YC
3. Format message
4. Send to user
5. Save to notification_history (but not to pending_notifications)

Response Format:
📊 Yandex Cloud Resources Report

🖥️ Compute Instances (3):
  • vm-1: RUNNING (CPU: 2, RAM: 4GB, IP: 51.250.1.1)
  • vm-2: STOPPED
  • vm-3: RUNNING (CPU: 4, RAM: 8GB, IP: 51.250.1.2)

🗄️ Databases (2):
  • postgres-cluster: RUNNING (v15, s2.micro)
  • mysql-cluster: STOPPED

📦 Storage Buckets (2):
  • my-bucket-1
  • my-bucket-2

🌐 Networks (1):
  • default-network

🔒 Security Groups (3):
  • default-security-group (5 rules)
  • web-security-group (8 rules)
  • db-security-group (4 rules)

⚖️ Load Balancers (1):
  • my-load-balancer: ACTIVE (51.250.2.1:80)

📦 Container Registries (1):
  • my-registry

⚡ Serverless Functions (2):
  • my-function-1: ACTIVE (python311, 128MB)
  • my-function-2: ACTIVE (nodejs18, 256MB)

📦 Serverless Containers (1):
  • my-container: ACTIVE (1 CPU, 128MB)

🌍 DNS Zones (1):
  • example.com (public)

🚪 API Gateways (1):
  • my-api-gateway: ACTIVE (b1g...apigw.yandexcloud.net)

Total: 17 resources (12 running/active, 2 stopped, 3 other)

Reply OK to acknowledge
```

#### /status
```
Behavior:
1. Check authorization
2. Get scheduler status
3. Get database stats
4. Send status message

Response Format:
🤖 Bot Status

✅ Bot is running
📅 Next report: 2024-01-15 21:00:00 (Europe/Moscow)
📊 Pending notifications: 0
📜 Total reports sent: 42
🕐 Uptime: 5 days, 3 hours
```

#### /help
```
Behavior:
1. Check authorization
2. Send help message

Response Format:
📚 Available Commands

/start - Welcome message and setup
/resources - Get current resource list
/status - Check bot and scheduler status
/help - Show this help message

📅 Daily Reports
I send resource reports every day at 21:00 (Europe/Moscow).
If you don't reply "OK" within 2 hours, I'll remind you.

🔒 Access Control
Only authorized users can interact with this bot.
```

### 5.2 Text Message Handler (OK Acknowledgment)

```
Behavior:
1. Check if message text is "OK" (case-insensitive)
2. If yes:
   - Find most recent pending notification for this chat
   - Mark as acknowledged
   - Send confirmation: "✅ Acknowledged"
3. If no:
   - Ignore or send "Please reply with OK to acknowledge the report"
```

### 5.3 Access Control Middleware

```python
async def access_control_middleware(handler):
    async def wrapper(update, context):
        user_id = update.effective_user.id
        
        if user_id != config.telegram.allowed_user_id:
            # Log unauthorized access
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            
            # Send denial message
            if update.message:
                await update.message.reply_text("⛔ Access denied")
            
            return  # Stop processing
        
        # User is authorized, continue
        return await handler(update, context)
    
    return wrapper
```

---

## 6. SCHEDULER LOGIC

### 6.1 Daily Report Job

```python
# Schedule: Every day at configured time (default: 21:00)
# Timezone: Configured in config.yaml (default: Europe/Moscow)

async def daily_report_job():
    # 1. Fetch all resources
    resources = await fetch_all_resources()
    
    # 2. Format message
    message_text = format_resources_message(resources)
    
    # 3. Send message
    message = await bot.send_message(
        chat_id=config.telegram.allowed_user_id,
        text=message_text
    )
    
    # 4. Save to pending_notifications
    await db.save_pending_notification(
        message_id=message.message_id,
        chat_id=message.chat.id,
        sent_at=datetime.now()
    )
    
    # 5. Save to notification_history
    await db.save_notification_history(
        sent_at=datetime.now(),
        resources_count=len(resources)
    )
```

### 6.2 Reminder Check Job

```python
# Schedule: Every 30 minutes
# Purpose: Check for unacknowledged notifications and send reminders

async def reminder_check_job():
    # 1. Get unacknowledged notifications
    pending = await db.get_unacknowledged_notifications()
    
    for notification in pending:
        # 2. Check if reminder should be sent
        time_since_sent = datetime.now() - notification.sent_at
        
        if time_since_sent >= timedelta(hours=config.scheduler.reminder_hours):
            if not notification.reminder_sent:
                # 3. Send reminder
                reminder_text = "⏰ Reminder: Please acknowledge the previous resource report by replying OK"
                
                await bot.send_message(
                    chat_id=notification.chat_id,
                    text=reminder_text,
                    reply_to_message_id=notification.message_id
                )
                
                # 4. Mark reminder as sent
                await db.mark_reminder_sent(notification.id)
```

### 6.3 Scheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone=config.scheduler.timezone)

# Parse time from config (e.g., "21:00")
hour, minute = map(int, config.scheduler.daily_report_time.split(':'))

# Add daily report job
scheduler.add_job(
    daily_report_job,
    CronTrigger(hour=hour, minute=minute),
    id='daily_report',
    name='Daily Resource Report',
    replace_existing=True
)

# Add reminder check job (every 30 minutes)
scheduler.add_job(
    reminder_check_job,
    'interval',
    minutes=30,
    id='reminder_check',
    name='Reminder Check',
    replace_existing=True
)

scheduler.start()
```

---

## 7. DATA STORAGE

### 7.1 SQLite Schema

```sql
-- Table: pending_notifications
-- Purpose: Track notifications waiting for acknowledgment

CREATE TABLE pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient querying of unacknowledged notifications
CREATE INDEX idx_pending_unacknowledged 
ON pending_notifications(acknowledged, reminder_sent);

-- Index for querying by chat_id
CREATE INDEX idx_pending_chat_id 
ON pending_notifications(chat_id);


-- Table: notification_history
-- Purpose: Historical record of all sent notifications

CREATE TABLE notification_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at TIMESTAMP NOT NULL,
    acknowledged_at TIMESTAMP,
    resources_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for querying recent history
CREATE INDEX idx_history_sent_at 
ON notification_history(sent_at DESC);
```

### 7.2 Database Operations

```python
# Pending Notifications

async def save_pending_notification(message_id: int, chat_id: int, sent_at: datetime):
    """Save new pending notification"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO pending_notifications (message_id, chat_id, sent_at)
               VALUES (?, ?, ?)""",
            (message_id, chat_id, sent_at)
        )
        await db.commit()

async def get_unacknowledged_notifications() -> List[Notification]:
    """Get all unacknowledged notifications"""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """SELECT id, message_id, chat_id, sent_at, reminder_sent
               FROM pending_notifications
               WHERE acknowledged = FALSE"""
        )
        rows = await cursor.fetchall()
        return [Notification(*row) for row in rows]

async def acknowledge_notification(message_id: int, chat_id: int):
    """Mark notification as acknowledged"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE pending_notifications
               SET acknowledged = TRUE
               WHERE message_id = ? AND chat_id = ?""",
            (message_id, chat_id)
        )
        await db.commit()

async def mark_reminder_sent(notification_id: int):
    """Mark that reminder was sent for this notification"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE pending_notifications
               SET reminder_sent = TRUE
               WHERE id = ?""",
            (notification_id,)
        )
        await db.commit()


# Notification History

async def save_notification_history(sent_at: datetime, resources_count: int):
    """Save notification to history"""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO notification_history (sent_at, resources_count)
               VALUES (?, ?)""",
            (sent_at, resources_count)
        )
        await db.commit()

async def get_total_reports_count() -> int:
    """Get total number of reports sent"""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM notification_history")
        row = await cursor.fetchone()
        return row[0]

async def get_pending_count() -> int:
    """Get count of pending (unacknowledged) notifications"""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """SELECT COUNT(*) FROM pending_notifications
               WHERE acknowledged = FALSE"""
        )
        row = await cursor.fetchone()
        return row[0]
```

---

## 8. CONFIGURATION

### 8.1 config.yaml Structure

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"  # From .env
  allowed_user_id: 123456789  # Required, no default

scheduler:
  daily_report_time: "21:00"  # HH:MM format, 24-hour
  timezone: "Europe/Moscow"  # IANA timezone
  reminder_hours: 2  # Hours before sending reminder

yandex_cloud:
  folder_id: "b1g..."  # Required
  cloud_id: "b1g..."  # Required
  service_account_key_path: "/app/config/sa-key.json"  # Path to SA key

storage:
  database_path: "/app/data/bot.db"  # SQLite file path

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 8.2 .env Variables

```bash
# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Yandex Cloud (optional, can be in config.yaml)
# YC_FOLDER_ID=b1g...
# YC_CLOUD_ID=b1g...
```

### 8.3 Configuration Loading

```python
from pydantic import BaseModel, Field
from typing import Optional
import yaml
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramConfig(BaseModel):
    bot_token: str
    allowed_user_id: int

class SchedulerConfig(BaseModel):
    daily_report_time: str = "21:00"
    timezone: str = "Europe/Moscow"
    reminder_hours: int = 2

class YandexCloudConfig(BaseModel):
    folder_id: str
    cloud_id: str
    service_account_key_path: str

class StorageConfig(BaseModel):
    database_path: str = "/app/data/bot.db"

class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class Config(BaseModel):
    telegram: TelegramConfig
    scheduler: SchedulerConfig = SchedulerConfig()
    yandex_cloud: YandexCloudConfig
    storage: StorageConfig = StorageConfig()
    logging: LoggingConfig = LoggingConfig()

def load_config(config_path: str = "config.yaml") -> Config:
    """Load and validate configuration"""
    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Replace ${VAR} with environment variables
    def replace_env_vars(obj):
        if isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_name = obj[2:-1]
            return os.getenv(var_name, '')
        elif isinstance(obj, dict):
            return {k: replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        return obj
    
    raw_config = replace_env_vars(raw_config)
    
    return Config(**raw_config)
```

---

## 9. SECURITY REQUIREMENTS

### 9.1 Yandex Cloud Permissions

**Service Account Roles:**
- `viewer` - Read-only access to all resources
- **DO NOT** assign `editor`, `admin`, or any write roles

**How to create SA with minimal permissions:**
```bash
# Create service account
yc iam service-account create --name bot-watcher

# Get folder ID
FOLDER_ID=$(yc config get folder-id)

# Assign viewer role
yc resource-manager folder add-access-binding $FOLDER_ID \
  --role viewer \
  --subject serviceAccount:<sa-id>

# Create authorized key
yc iam key create \
  --service-account-name bot-watcher \
  --output sa-key.json
```

### 9.2 Telegram Access Control

- Bot MUST check `message.from_user.id` against `config.telegram.allowed_user_id`
- Reject ALL commands from unauthorized users
- Log unauthorized access attempts
- No exceptions, even for "simple" commands like /help

### 9.3 Secret Management

- **NEVER** hardcode secrets in code
- Use `.env` file for sensitive data (bot token)
- Use `sa-key.json` file for YC credentials
- Add `.env` and `sa-key.json` to `.gitignore`
- Mount secrets as read-only in Docker

### 9.4 Docker Security

```dockerfile
# Use non-root user
RUN useradd -m -u 1000 botuser
USER botuser

# Read-only mounts in docker-compose
volumes:
  - ./config:/app/config:ro
  - ./data:/app/data

# No privileged mode
# No host network
# Drop all capabilities
```

### 9.5 Input Validation

- Validate all configuration values using Pydantic
- Validate Telegram message data before processing
- Sanitize file paths
- Validate YC API responses

---

## 10. TESTING REQUIREMENTS

### 10.1 Test Coverage

- **Minimum coverage**: 80%
- **Critical paths**: 100%
  - YC authentication
  - Access control middleware
  - Resource fetching
  - Message formatting
  - Scheduler logic

### 10.2 Test Scenarios

#### test_auth.py
```python
async def test_generate_jwt_token():
    """Test JWT token generation with SA key"""
    
async def test_exchange_jwt_for_iam_token():
    """Test JWT to IAM token exchange"""
    
async def test_cache_iam_token():
    """Test IAM token caching"""
    
async def test_refresh_expired_token():
    """Test token refresh before expiry"""
    
async def test_handle_auth_error():
    """Test handling of authentication errors"""
```

#### test_resources.py
```python
async def test_fetch_compute_instances():
    """Test fetching compute instances"""
    
async def test_fetch_compute_instances_empty():
    """Test when no instances exist"""
    
async def test_fetch_compute_instances_api_error():
    """Test handling of API errors"""
    
async def test_fetch_all_resources():
    """Test fetching all resource types"""
    
async def test_format_resources_message():
    """Test message formatting"""
    
async def test_format_resources_message_empty():
    """Test formatting when no resources"""
```

#### test_handlers.py
```python
async def test_start_command_authorized():
    """Test /start with authorized user"""
    
async def test_start_command_unauthorized():
    """Test /start with unauthorized user"""
    
async def test_resources_command():
    """Test /resources command"""
    
async def test_status_command():
    """Test /status command"""
    
async def test_help_command():
    """Test /help command"""
    
async def test_ok_acknowledgment():
    """Test OK text message handling"""
    
async def test_access_control_middleware():
    """Test access control middleware"""
```

#### test_scheduler.py
```python
async def test_daily_report_job():
    """Test daily report job execution"""
    
async def test_reminder_check_job():
    """Test reminder check job"""
    
async def test_reminder_not_sent_before_timeout():
    """Test reminder not sent before configured hours"""
    
async def test_reminder_not_sent_if_acknowledged():
    """Test reminder not sent if already acknowledged"""
```

### 10.3 Mocking Strategy

```python
# Mock YC API responses
from aioresponses import aioresponses

async def test_fetch_resources():
    with aioresponses() as m:
        m.get(
            'https://compute.api.cloud.yandex.net/compute/v1/instances',
            payload={'instances': [...]}
        )
        resources = await fetch_compute_instances()
        assert len(resources) == 3

# Mock Telegram API
from unittest.mock import AsyncMock

async def test_send_message():
    bot = AsyncMock()
    bot.send_message.return_value = AsyncMock(message_id=123)
    # ... test code
```

### 10.4 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_handlers.py

# Run with verbose output
pytest -v
```

---

## 11. DOCKER DEPLOYMENT

### 11.1 Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data && chown -R botuser:botuser /app/data

# Switch to non-root user
USER botuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Run application
CMD ["python", "-m", "bot.main"]
```

### 11.2 docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: yc-watcher-bot
    restart: unless-stopped
    
    volumes:
      # Config files (read-only)
      - ./config:/app/config:ro
      
      # Data directory (writable for SQLite)
      - ./data:/app/data
      
      # Service account key (read-only)
      - ./config/sa-key.json:/app/config/sa-key.json:ro
    
    env_file:
      - .env
    
    environment:
      - TZ=${TZ:-Europe/Moscow}
    
    # Security options
    security_opt:
      - no-new-privileges:true
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

### 11.3 Environment Variables

```bash
# .env file
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TZ=Europe/Moscow
```

---

## 12. SCRIPTS SPECIFICATION

### 12.1 install.sh

```bash
#!/bin/bash
set -e

echo "🚀 Installing Yandex Cloud Resources Watcher Bot..."

# 1. Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# 2. Create directories
echo "📁 Creating directories..."
mkdir -p config data

# 3. Generate config files
echo "⚙️  Generating configuration files..."

if [ ! -f config/config.yaml ]; then
    cp config.yaml.example config/config.yaml
    echo "✅ Created config/config.yaml"
else
    echo "⚠️  config/config.yaml already exists, skipping"
fi

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env"
else
    echo "⚠️  .env already exists, skipping"
fi

# 4. Prompt for configuration
echo ""
echo "📝 Please configure the following:"
echo ""
echo "1. Edit .env and set TELEGRAM_BOT_TOKEN"
echo "2. Edit config/config.yaml and set:"
echo "   - telegram.allowed_user_id"
echo "   - yandex_cloud.folder_id"
echo "   - yandex_cloud.cloud_id"
echo "   - scheduler.timezone (if needed)"
echo ""

# 5. Instructions for SA key
echo "🔐 Service Account Key Setup:"
echo "1. Create a service account in Yandex Cloud with 'viewer' role"
echo "2. Create an authorized key and download as JSON"
echo "3. Place the key file at: config/sa-key.json"
echo ""

# 6. Build and start
read -p "Ready to build and start the bot? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔨 Building Docker image..."
    docker-compose build
    
    echo "🚀 Starting bot..."
    docker-compose up -d
    
    echo "✅ Bot started successfully!"
    echo ""
    echo "📊 Check status with: docker-compose ps"
    echo "📜 View logs with: docker-compose logs -f"
else
    echo ""
    echo "⚠️  Bot not started. To start manually:"
    echo "   docker-compose up -d"
fi

echo ""
echo "🎉 Installation complete!"
```

### 12.2 update.sh

```bash
#!/bin/bash
set -e

echo "🔄 Updating Yandex Cloud Resources Watcher Bot..."

# 1. Backup current state
echo "💾 Creating backup..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

if [ -d "data" ]; then
    cp -r data $BACKUP_DIR/
    echo "✅ Backed up data directory to $BACKUP_DIR"
fi

# 2. Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# 3. Rebuild Docker image
echo "🔨 Rebuilding Docker image..."
docker-compose build

# 4. Restart bot
echo "🚀 Restarting bot..."
docker-compose up -d

# 5. Verify
echo "🔍 Verifying..."
sleep 5
docker-compose ps

echo ""
echo "✅ Update complete!"
echo ""
echo "📜 View logs with: docker-compose logs -f"
```

---

## 13. DOCUMENTATION REQUIREMENTS

### 13.1 README.md

```markdown
# Yandex Cloud Resources Watcher Bot

Telegram bot for monitoring Yandex Cloud resources with scheduled notifications.

## Features

- 📊 Daily resource reports at configurable time
- ⏰ Reminder system for unacknowledged reports
- 🔍 On-demand resource status via `/resources` command
- 🔒 Secure access control (single user)
- 🐳 Docker-based deployment
- 🔐 Least privilege Yandex Cloud access

## Quick Start

1. Clone repository
2. Run `./scripts/install.sh`
3. Configure `.env` and `config/config.yaml`
4. Place SA key at `config/sa-key.json`
5. Start bot: `docker-compose up -d`

## Documentation

- [Administrator Guide](docs/ADMIN.md)
- [User Guide](docs/USER.md)
- [Technical Specification](docs/SPEC.md)

## License

MIT
```

### 13.2 AGENTS.md

```markdown
# AGENTS.md - Developer Guide

## Project Structure

[Detailed explanation of each module and its responsibility]

## Architecture Decisions

### Why aiogram?
[Explanation of framework choice]

### Why SQLite?
[Explanation of storage choice]

### Why separate YC client module?
[Explanation of separation of concerns]

## Adding New Resource Types

1. Add API method in `yandex_cloud/client.py`
2. Add fetch function in `yandex_cloud/resources.py`
3. Add formatting in `format_resources_message()`
4. Add tests in `tests/test_resources.py`

## Code Conventions

- Use type hints
- Follow PEP 8
- Use async/await consistently
- Write docstrings for all functions
- Keep functions small and focused

## Testing Guidelines

- Write unit tests for all business logic
- Mock external APIs (YC, Telegram)
- Aim for 80%+ coverage
- Test error scenarios

## Common Tasks

### How to add a new command
[Step-by-step guide]

### How to change message format
[Step-by-step guide]

### How to add a new resource type
[Step-by-step guide]
```

### 13.3 ADMIN.md

```markdown
# Administrator Guide

## Prerequisites

- Docker and Docker Compose installed
- Yandex Cloud account with billing enabled
- Telegram account

## Yandex Cloud Setup

### 1. Create Service Account

```bash
yc iam service-account create --name bot-watcher
```

### 2. Assign Viewer Role

```bash
FOLDER_ID=$(yc config get folder-id)
SA_ID=$(yc iam service-account get --name bot-watcher --format json | jq -r .id)

yc resource-manager folder add-access-binding $FOLDER_ID \
  --role viewer \
  --subject serviceAccount:$SA_ID
```

### 3. Create Authorized Key

```bash
yc iam key create \
  --service-account-name bot-watcher \
  --output sa-key.json
```

## Telegram Bot Setup

### 1. Create Bot

1. Message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Follow instructions
4. Save bot token

### 2. Get Your User ID

1. Message [@userinfobot](https://t.me/userinfobot)
2. Save your user ID

## Installation

### Option 1: Using Install Script

```bash
git clone <repository-url>
cd yacloud-resources-watcher
./scripts/install.sh
```

### Option 2: Manual Installation

```bash
# Create directories
mkdir -p config data

# Copy config files
cp config.yaml.example config/config.yaml
cp .env.example .env

# Edit configuration
nano .env
nano config/config.yaml

# Place SA key
cp /path/to/sa-key.json config/sa-key.json

# Build and start
docker-compose up -d --build
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

## Updating

```bash
./scripts/update.sh
```

## Troubleshooting

### Bot not responding
- Check logs: `docker-compose logs -f`
- Verify bot token in `.env`
- Check user ID in config

### YC API errors
- Verify SA key is valid
- Check SA has `viewer` role
- Verify folder_id and cloud_id

### No resources shown
- Check folder has resources
- Verify SA has access to folder

## Backup/Restore

### Backup
```bash
cp -r data backup_$(date +%Y%m%d)
```

### Restore
```bash
cp -r backup_20240115 data
docker-compose restart
```
```

### 13.4 USER.md

```markdown
# User Guide

## Getting Started

1. Find your bot in Telegram
2. Send `/start`
3. Bot will welcome you and show available commands

## Commands

### /start
Start the bot and see welcome message.

### /resources
Get current list of all your Yandex Cloud resources.

Example response:
```
📊 Yandex Cloud Resources Report

🖥️ Compute Instances (2):
  • vm-1: RUNNING (CPU: 2, RAM: 4GB)
  • vm-2: STOPPED

Total: 2 resources (1 running, 1 stopped)
```

### /status
Check bot status and next scheduled report time.

### /help
Show list of available commands.

## Daily Reports

- You'll receive a resource report every day at 21:00 (configurable)
- The report shows all resources in your Yandex Cloud folder
- Reply "OK" to acknowledge the report
- If you don't reply within 2 hours, you'll get a reminder

## Acknowledging Reports

When you receive a daily report:
1. Review the resource list
2. Reply with "OK" (case-insensitive)
3. Bot will confirm: "✅ Acknowledged"

## What Information is Included?

The report includes:
- Compute instances (VMs) with status, CPU, RAM, IP
- Managed databases (PostgreSQL, MySQL, MongoDB, ClickHouse)
- Object Storage buckets
- VPC networks, subnets, security groups
- Load balancers
- Container registries
- Serverless functions and containers
- DNS zones
- API gateways

## FAQ

**Q: Why am I not receiving reports?**
A: Check that the bot is running and your user ID is configured correctly.

**Q: Can I change the report time?**
A: Yes, ask your administrator to update `scheduler.daily_report_time` in config.

**Q: What if I accidentally reply something other than OK?**
A: Just reply "OK" to acknowledge. Other messages are ignored.

**Q: Can other people use this bot?**
A: No, the bot is configured to respond only to one authorized user.
```

---

## 14. IMPLEMENTATION ORDER

### Phase 1: Foundation (Priority: HIGH)
1. Create project structure
2. Setup configuration system (config.py, config.yaml)
3. Setup logging
4. Create requirements.txt

### Phase 2: YC Integration (Priority: HIGH)
5. Implement SA authentication (auth.py)
6. Implement IAM token management
7. Implement YC API client (client.py)
8. Implement resource fetching for all types (resources.py)

### Phase 3: Telegram Bot (Priority: HIGH)
9. Setup aiogram bot (main.py)
10. Implement access control middleware (middleware.py)
11. Implement command handlers (handlers.py)
12. Implement message formatting

### Phase 4: Scheduler (Priority: MEDIUM)
13. Setup APScheduler (scheduler.py)
14. Implement daily report job
15. Implement reminder check job

### Phase 5: Storage (Priority: MEDIUM)
16. Setup SQLite database (database.py)
17. Implement notification tracking
18. Integrate storage with handlers and scheduler

### Phase 6: Testing (Priority: MEDIUM)
19. Write unit tests for YC client
20. Write unit tests for bot handlers
21. Write unit tests for scheduler
22. Write unit tests for storage

### Phase 7: Docker (Priority: LOW)
23. Create Dockerfile
24. Create docker-compose.yml
25. Test Docker deployment

### Phase 8: Scripts (Priority: LOW)
26. Create install.sh
27. Create update.sh
28. Test scripts

### Phase 9: Documentation (Priority: LOW)
29. Write README.md
30. Write AGENTS.md
31. Write ADMIN.md
32. Write USER.md

---

## 15. ACCEPTANCE CRITERIA

### Definition of Done

- [ ] All user stories implemented
- [ ] Unit tests pass with 80%+ coverage
- [ ] Docker image builds without errors
- [ ] Bot starts and runs successfully
- [ ] Documentation is complete and accurate
- [ ] Installation and update scripts work
- [ ] Security checklist completed

### Testing Checklist

- [ ] Bot responds only to authorized user
- [ ] Bot ignores unauthorized users
- [ ] Daily notifications arrive at configured time
- [ ] Reminders work after configured hours
- [ ] `/resources` command returns current resource list
- [ ] Message format is correct
- [ ] YC API errors are handled gracefully
- [ ] Network errors are handled with retries
- [ ] "OK" acknowledgment works
- [ ] Database persists across restarts

### Security Checklist

- [ ] SA has only `viewer` role
- [ ] Access control middleware works
- [ ] Secrets not in code
- [ ] `.env` in `.gitignore`
- [ ] `sa-key.json` in `.gitignore`
- [ ] Docker runs as non-root
- [ ] Config mounted as read-only
- [ ] Input validation implemented

### Performance Checklist

- [ ] Bot responds within 5 seconds
- [ ] Resource fetching completes within 30 seconds
- [ ] Memory usage < 256MB
- [ ] CPU usage < 50%

---

## 16. APPENDIX

### 16.1 Example sa-key.json

```json
{
   "id": "aje...",
   "service_account_id": "aje...",
   "created_at": "2024-01-01T00:00:00Z",
   "key_algorithm": "RSA_2048",
   "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
   "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
}
```

### 16.2 Example .env

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TZ=Europe/Moscow
```

### 16.3 Example config.yaml

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  allowed_user_id: 123456789

scheduler:
  daily_report_time: "21:00"
  timezone: "Europe/Moscow"
  reminder_hours: 2

yandex_cloud:
  folder_id: "b1g..."
  cloud_id: "b1g..."
  service_account_key_path: "/app/config/sa-key.json"

storage:
  database_path: "/app/data/bot.db"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 16.4 Useful Links

- [Yandex Cloud API Documentation](https://cloud.yandex.com/en/docs/api-design-guide/)
- [Yandex Cloud IAM](https://cloud.yandex.com/en/docs/iam/)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

---

**End of Specification**
