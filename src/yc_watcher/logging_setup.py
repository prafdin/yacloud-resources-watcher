"""Single entry point for configuring the root logger.

Called once at startup so every module's ``logging.getLogger(__name__)`` shares
one format and level; the noisy aiogram event logger is turned down.
"""

import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
