import pytest
from unittest.mock import Mock
from yacloud_watcher.bot.router import create_router

def test_create_router():
    router = create_router()
    assert router is not None
