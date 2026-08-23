from __future__ import annotations

import asyncio
import re
import secrets
import string
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _mask(url: str) -> str:
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


async def main() -> int:
    settings = get_settings()
    current = settings.migration_database_url
    if not current:
        print("MIGRATION_DATABASE_URL is not set; nothing to rotate.")
        return 1

    user = urlsplit(current).netloc.split(":", 1)[0]

    alphabet = string.ascii_letters + string.digits
    new_password = "".join(secrets.choice(alphabet) for _ in range(40))
    assert new_password.isalnum()

    engine = create_async_engine(current, connect_args={"statement_cache_size": 0})
    async with engine.begin() as c:
        who = (await c.execute(text("select current_user"))).scalar()
        if who != user:
            print(f"connected as {who!r} but URL says {user!r}; aborting")
            return 1
        await c.execute(text(f"ALTER ROLE {who} WITH PASSWORD '{new_password}'"))
        print(f"rotated password for role {who!r}")
    await engine.dispose()

    parts = urlsplit(current.replace("postgresql+asyncpg://", "postgresql://"))
    host = parts.netloc.split("@", 1)[1]
    new_url = urlunsplit((parts.scheme, f"{user}:{new_password}@{host}", parts.path, parts.query, ""))

    env = ENV_FILE.read_text()
    if not re.search(r"^MIGRATION_DATABASE_URL=", env, re.M):
        print("could not find MIGRATION_DATABASE_URL in .env; aborting before losing the password")
        return 1
    ENV_FILE.write_text(
        re.sub(r"^MIGRATION_DATABASE_URL=.*$", f"MIGRATION_DATABASE_URL={new_url}", env, flags=re.M)
    )
    print(f"updated .env -> {_mask(new_url)}")

    get_settings.cache_clear()
    verify = create_async_engine(
        get_settings().migration_database_url, connect_args={"statement_cache_size": 0}
    )
    try:
        async with verify.connect() as c:
            ok = (await c.execute(text("select 1"))).scalar()
        print("verified: new password connects" if ok == 1 else "verification returned unexpected result")
    except Exception as e:
        print(f"VERIFICATION FAILED: {type(e).__name__}: {e}")
        return 1
    finally:
        await verify.dispose()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
