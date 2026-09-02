from yacloud_watcher.scheduler.jobs import create_scheduler


def test_create_scheduler():
    scheduler = create_scheduler()
    assert scheduler is not None
