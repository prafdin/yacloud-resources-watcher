# AGENTS.md - Developer Guide

## Project Overview

Yandex Cloud Resources Watcher Bot - Telegram bot for monitoring YC resources with scheduled notifications.

## Architecture

### Components

1. **bot/** - Telegram bot logic
   - `main.py` - Entry point, initialization
   - `handlers.py` - Command handlers
   - `scheduler.py` - APScheduler setup
   - `middleware.py` - Access control

2. **yandex_cloud/** - YC API integration
   - `auth.py` - Service Account authentication
   - `client.py` - HTTP client for YC API
   - `resources.py` - Resource fetching logic

3. **storage/** - Data persistence
   - `database.py` - SQLite operations
   - `models.py` - Data models

4. **config/** - Configuration
   - `settings.py` - Config loading and validation

## Key Design Decisions

### Why aiogram?
- Modern async framework
- Better performance than python-telegram-bot
- Native async/await support
- Active development

### Why SQLite?
- Simple, no external dependencies
- Sufficient for single-user bot
- File-based, easy to backup
- No separate service required

### Why separate YC client module?
- Separation of concerns
- Easy to test with mocks
- Reusable for different resource types
- Clear API boundaries

### Why APScheduler?
- Mature, stable library
- Async support via AsyncIOScheduler
- Cron-like scheduling
- Job persistence (optional)

## Adding New Resource Types

### Step 1: Add API Method in `yandex_cloud/client.py`

```python
async def get_new_resource(self, folder_id: str) -> dict:
    """Fetch new resource type from YC API."""
    url = f"https://new-resource.api.cloud.yandex.net/v1/resources"
    params = {"folderId": folder_id}
    
    async with self.session.get(url, params=params, headers=self.headers) as resp:
        resp.raise_for_status()
        return await resp.json()
```

### Step 2: Add Fetch Function in `yandex_cloud/resources.py`

```python
async def fetch_new_resources(client: YCClient, folder_id: str) -> list[NewResource]:
    """Fetch all new resources."""
    try:
        response = await client.get_new_resource(folder_id)
        resources = [
            NewResource(
                id=r["id"],
                name=r["name"],
                status=r["status"]
            )
            for r in response.get("resources", [])
        ]
        return resources
    except Exception as e:
        logger.error(f"Failed to fetch new resources: {e}")
        return []
```

### Step 3: Update `fetch_all_resources()` in `yandex_cloud/resources.py`

```python
async def fetch_all_resources(config: Config) -> AllResources:
    """Fetch all resources from YC."""
    client = YCClient(config.yandex_cloud)
    
    return AllResources(
        compute_instances=await fetch_compute_instances(client, config.yandex_cloud.folder_id),
        # ... existing resources
        new_resources=await fetch_new_resources(client, config.yandex_cloud.folder_id),
    )
```

### Step 4: Update Message Formatting in `bot/handlers.py`

```python
def format_resources_message(resources: AllResources) -> str:
    """Format resources into Telegram message."""
    sections = []
    
    # ... existing sections
    
    # New resource section
    if resources.new_resources:
        section = "🆕 New Resources ({count}):\n".format(
            count=len(resources.new_resources)
        )
        for r in resources.new_resources:
            section += f"  • {r.name}: {r.status}\n"
        sections.append(section)
    
    return "\n".join(sections)
```

### Step 5: Add Tests in `tests/test_resources.py`

```python
async def test_fetch_new_resources():
    """Test fetching new resources."""
    client = MockYCClient()
    client.get_new_resource = AsyncMock(return_value={
        "resources": [
            {"id": "1", "name": "test", "status": "ACTIVE"}
        ]
    })
    
    resources = await fetch_new_resources(client, "b1g_test")
    
    assert len(resources) == 1
    assert resources[0].name == "test"
```

## Adding New Commands

### Step 1: Add Handler in `bot/handlers.py`

```python
@dp.message(Command("newcommand"))
async def cmd_newcommand(message: Message):
    """Handle /newcommand."""
    # Your logic here
    await message.answer("Response message")
```

### Step 2: Register Handler in `bot/main.py`

Handler is automatically registered via decorator.

### Step 3: Update `/help` Command

```python
@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message."""
    help_text = """
📚 Available Commands

/start - Welcome message
/resources - Get resource list
/status - Bot status
/newcommand - New command description
/help - Show this help
    """
    await message.answer(help_text)
```

### Step 4: Add Tests in `tests/test_handlers.py`

```python
async def test_newcommand():
    """Test /newcommand handler."""
    # Setup
    message = MockMessage(text="/newcommand", from_user=MockUser(id=123456789))
    
    # Execute
    await cmd_newcommand(message)
    
    # Verify
    message.answer.assert_called_once()
```

## Code Conventions

### General
- Use type hints for all functions
- Follow PEP 8
- Keep functions small and focused (< 50 lines)
- Use descriptive variable names
- Write docstrings for all public functions

### Async/Await
- Use async/await consistently
- Never block the event loop
- Use `asyncio.gather()` for concurrent operations
- Handle exceptions properly

### Error Handling
- Log errors with context
- Return sensible defaults on error (empty lists, etc.)
- Never expose internal errors to users
- Use specific exception types

### Configuration
- Use Pydantic for validation
- Provide sensible defaults
- Document all config options
- Validate on startup

### Testing
- Write unit tests for all business logic
- Mock external dependencies
- Use fixtures for common setup
- Test error scenarios
- Aim for 80%+ coverage

## Common Tasks

### How to Change Message Format

1. Edit `format_resources_message()` in `bot/handlers.py`
2. Update tests in `tests/test_handlers.py`
3. Update documentation in `docs/USER.md`

### How to Change Scheduler Time

1. Edit `config.yaml`: `scheduler.daily_report_time: "22:00"`
2. Restart bot: `docker compose restart`
3. No code changes needed

### How to Add New Config Option

1. Add to `config.yaml.example`
2. Add to Pydantic model in `config/settings.py`
3. Use in code via `config.new_option`
4. Update documentation

### How to Debug

```bash
# Enable debug logging
# Edit config.yaml: logging.level: "DEBUG"

# View logs
docker compose -f docker/docker-compose.yml logs -f

# Run locally (without Docker)
python -m bot.main
```

## Testing Guidelines

### Unit Tests

```python
# Test individual functions
async def test_function_name():
    # Arrange
    input_data = ...
    expected = ...
    
    # Act
    result = await function_under_test(input_data)
    
    # Assert
    assert result == expected
```

### Mocking YC API

```python
from aioresponses import aioresponses

async def test_with_mock_api():
    with aioresponses() as m:
        m.get(
            'https://compute.api.cloud.yandex.net/compute/v1/instances',
            payload={'instances': [...]}
        )
        
        result = await fetch_compute_instances(...)
        
        assert len(result) == 2
```

### Mocking Telegram Bot

```python
from unittest.mock import AsyncMock

async def test_handler():
    message = AsyncMock()
    message.from_user.id = 123456789
    
    await handler(message)
    
    message.answer.assert_called_once()
```

## Performance Considerations

### Resource Fetching
- Fetch all resource types concurrently with `asyncio.gather()`
- Cache IAM tokens (valid for 12 hours)
- Handle API rate limits with exponential backoff

### Database
- Use connection pooling (if needed)
- Index frequently queried columns
- Keep queries simple

### Memory
- Stream large responses (if needed)
- Clean up old notifications periodically
- Monitor memory usage

## Security Checklist

- [ ] SA has only `viewer` role
- [ ] Access control middleware active
- [ ] Secrets not in code
- [ ] `.env` in `.gitignore`
- [ ] `sa-key.json` in `.gitignore`
- [ ] Docker runs as non-root
- [ ] Config mounted as read-only
- [ ] Input validation implemented
- [ ] Error messages don't leak secrets

## Deployment Checklist

- [ ] Configuration complete
- [ ] SA key in place
- [ ] Docker image builds
- [ ] Bot starts successfully
- [ ] Commands work
- [ ] Daily report scheduled
- [ ] Logs accessible
- [ ] Backup strategy in place

## Troubleshooting Common Issues

### Import Errors
```bash
# Ensure you're in project root
python -m bot.main

# Check dependencies
pip install -r requirements.txt
```

### Database Errors
```bash
# Check database is being stored in the named volume
docker volume ls | grep bot_data

# Reset database (stored in Docker named volume)
docker compose -f docker/docker-compose.yml exec yc-watcher-bot rm /app/data/bot.db
docker compose restart
```

### YC API Errors
```bash
# Verify SA key
cat config/sa-key.json | jq .

# Test IAM token generation
python -c "from yandex_cloud.auth import generate_iam_token; print(generate_iam_token())"
```

## Resources

- [Yandex Cloud API Docs](https://cloud.yandex.com/en/docs/api-design-guide/)
- [aiogram Docs](https://docs.aiogram.dev/)
- [APScheduler Docs](https://apscheduler.readthedocs.io/)
- [Pydantic Docs](https://docs.pydantic.dev/)
