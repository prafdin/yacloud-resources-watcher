# Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Telegram Bot                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Handlers   │  │  Middleware  │  │  Scheduler   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Yandex Cloud Client                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Auth     │  │    Client    │  │  Resources   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Yandex Cloud API                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    SQLite Database                    │  │
│  │  ┌────────────────────┐  ┌────────────────────┐      │  │
│  │  │ pending_notif...   │  │ notification_h...  │      │  │
│  │  └────────────────────┘  └────────────────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Interaction

### Daily Report Flow

```
1. Scheduler triggers daily_report_job at configured time
2. Job calls fetch_all_resources()
3. fetch_all_resources() calls individual resource fetchers:
   - fetch_compute_instances()
   - fetch_postgresql_clusters()
   - fetch_mysql_clusters()
   - ... (all resource types)
4. Each fetcher:
   a. Gets IAM token (from cache or refresh)
   b. Makes HTTP request to YC API
   c. Parses response
   d. Returns list of resources
5. Resources aggregated and formatted into message
6. Message sent via Telegram Bot API
7. Notification saved to pending_notifications table
8. Notification saved to notification_history table
```

### Reminder Flow

```
1. Scheduler triggers reminder_check_job every 30 minutes
2. Job queries unacknowledged notifications from DB
3. For each notification:
   a. Calculate time since sent
   b. If time >= reminder_hours AND reminder not sent:
      - Send reminder message
      - Mark reminder_sent = TRUE in DB
```

### User Request Flow (/resources command)

```
1. User sends /resources command
2. Middleware checks authorization
3. If authorized:
   a. Handler calls fetch_all_resources()
   b. Resources formatted into message
   c. Message sent to user
   d. Notification saved to history (but NOT to pending)
4. If not authorized:
   - Send "Access denied" message
   - Log attempt
```

### OK Acknowledgment Flow

```
1. User sends "OK" message
2. Middleware checks authorization
3. If authorized:
   a. Handler finds most recent pending notification
   b. Marks notification as acknowledged
   c. Sends confirmation message
4. If not authorized:
   - Send "Access denied" message
```

## Data Flow

### Configuration Flow

```
1. Application starts
2. Load config.yaml
3. Replace ${VAR} placeholders with .env values
4. Validate with Pydantic
5. Config object available throughout application
```

### Authentication Flow

```
1. Load SA key from JSON file
2. Generate JWT token (signed with private key)
3. Exchange JWT for IAM token via YC IAM API
4. Cache IAM token with expiry time
5. Use IAM token for API calls
6. Refresh token 1 hour before expiry
```

## Module Dependencies

```
bot.main
  ├─> bot.handlers
  │   ├─> yandex_cloud.resources
  │   │   └─> yandex_cloud.client
  │   │       └─> yandex_cloud.auth
  │   ├─> storage.database
  │   └─> config.settings
  ├─> bot.scheduler
  │   ├─> yandex_cloud.resources
  │   ├─> storage.database
  │   └─> config.settings
  ├─> bot.middleware
  │   └─> config.settings
  └─> config.settings
```

## Security Layers

```
┌─────────────────────────────────────────┐
│ Layer 1: Telegram Access Control        │
│ - Middleware checks user_id             │
│ - Rejects unauthorized users            │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ Layer 2: Yandex Cloud Permissions       │
│ - Service Account with viewer role only │
│ - Read-only access to resources         │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ Layer 3: Docker Security                │
│ - Non-root user                         │
│ - Read-only config mounts               │
│ - No privileged mode                    │
└─────────────────────────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│ Layer 4: Secret Management              │
│ - Secrets in .env (not in code)         │
│ - SA key in separate file               │
│ - .gitignore excludes secrets           │
└─────────────────────────────────────────┘
```

## Error Handling Strategy

```
YC API Errors:
  401 Unauthorized → Refresh IAM token, retry
  403 Forbidden → Log error, notify user
  404 Not Found → Return empty list
  429 Rate Limit → Exponential backoff, retry
  500+ Server Error → Retry 3 times with backoff

Network Errors:
  ConnectionError → Retry 3 times
  Timeout → Retry 3 times
  DNS Error → Log and notify user

Database Errors:
  Connection Error → Retry with backoff
  Query Error → Log and continue (non-critical)
```

## Scalability Considerations

### Current Design (Single User)
- SQLite sufficient for single user
- No need for connection pooling
- Simple file-based storage

### Future Enhancements (Multi-User)
- Migrate to PostgreSQL
- Add user management table
- Implement per-user configuration
- Add queue for concurrent requests

## Monitoring and Logging

### Log Levels
- DEBUG: Detailed development info
- INFO: Normal operations (default)
- WARNING: Recoverable issues
- ERROR: Failures requiring attention
- CRITICAL: System-breaking issues

### Key Log Points
- Bot startup/shutdown
- Scheduler job execution
- YC API calls (request/response)
- Authentication events
- Error occurrences
- Unauthorized access attempts

## Testing Strategy

### Unit Tests
- Test individual functions in isolation
- Mock external dependencies (YC API, Telegram API)
- Fast execution (< 1 second per test)

### Integration Tests
- Test component interactions
- Use test database
- Mock external APIs

### Coverage Targets
- Business logic: 100%
- API clients: 90%
- Handlers: 80%
- Overall: 80%+

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│              VPS Server                  │
│  ┌───────────────────────────────────┐  │
│  │         Docker Engine              │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │    yc-watcher-bot container │  │  │
│  │  │                             │  │  │
│  │  │  /app/config (read-only)    │  │  │
│  │  │  /app/data (writable)       │  │  │
│  │  │  /app/config/sa-key.json    │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## Backup Strategy

### What to Backup
- SQLite database (data/bot.db)
- Configuration files (config/config.yaml)
- Service account key (config/sa-key.json)

### Backup Frequency
- Daily automated backup of data/
- Manual backup before updates

### Restore Procedure
1. Stop bot: `docker-compose down`
2. Restore data/ from backup
3. Start bot: `docker-compose up -d`
4. Verify operation
