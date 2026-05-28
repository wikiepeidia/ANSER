# Backward-compatibility shim — all logic lives in core/db/
from core.db.connection import Database, PGShimConnection, PGShimCursor  # noqa: F401
