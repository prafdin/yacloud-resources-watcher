"""Turns any caught exception into one short human-readable line.

Used when a single resource type fails to list, so the Telegram report can show
why that section is missing without dumping a stack trace.
"""

import grpc


def describe_error(exc: BaseException) -> str:
    if isinstance(exc, grpc.RpcError):
        code = exc.code()
        name = code.name if code is not None else "UNKNOWN"
        details = (exc.details() or "").strip()
        return f"{name}: {details}" if details else name
    return f"{type(exc).__name__}: {exc}"
