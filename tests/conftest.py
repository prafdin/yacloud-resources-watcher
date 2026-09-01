"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
import tempfile
import os


@pytest.fixture
def temp_db_path():
    """Create temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    from config.settings import Config, TelegramConfig, SchedulerConfig, YandexCloudConfig, StorageConfig, LoggingConfig
    
    return Config(
        telegram=TelegramConfig(
            bot_token="test_token",
            allowed_user_id=123456789
        ),
        scheduler=SchedulerConfig(
            daily_report_time="21:00",
            timezone="Europe/Moscow",
            reminder_hours=2
        ),
        yandex_cloud=YandexCloudConfig(
            folder_id="b1g_test",
            cloud_id="b1g_cloud_test",
            service_account_key_path="/tmp/test-sa-key.json"
        ),
        storage=StorageConfig(
            database_path="/tmp/test.db"
        ),
        logging=LoggingConfig(
            level="DEBUG"
        )
    )


@pytest.fixture
def mock_bot():
    """Create mock Telegram bot for testing."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def sample_sa_key():
    """Create sample service account key for testing."""
    return {
        "id": "aje_test",
        "service_account_id": "aje_sa_test",
        "created_at": "2024-01-01T00:00:00Z",
        "key_algorithm": "RSA_2048",
        "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----\n",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n"
    }


@pytest.fixture
def sample_compute_instances():
    """Create sample compute instances response."""
    return {
        "instances": [
            {
                "id": "fhm_test1",
                "name": "vm-1",
                "status": "RUNNING",
                "zoneId": "ru-central1-a",
                "resources": {
                    "cores": 2,
                    "memory": 4294967296,
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
            },
            {
                "id": "fhm_test2",
                "name": "vm-2",
                "status": "STOPPED",
                "zoneId": "ru-central1-b",
                "resources": {
                    "cores": 4,
                    "memory": 8589934592,
                    "coreFraction": 100
                },
                "networkInterfaces": [],
                "createdAt": "2024-01-02T00:00:00Z"
            }
        ]
    }


@pytest.fixture
def sample_postgresql_clusters():
    """Create sample PostgreSQL clusters response."""
    return {
        "clusters": [
            {
                "id": "c9q_test1",
                "name": "postgres-cluster",
                "status": "RUNNING",
                "config": {
                    "version": "15",
                    "resources": {
                        "resourcePresetId": "s2.micro",
                        "diskSize": 10737418240,
                        "diskTypeId": "network-ssd"
                    }
                },
                "createdAt": "2024-01-01T00:00:00Z"
            }
        ]
    }
