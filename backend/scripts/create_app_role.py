"""Create the restricted application role. Run once per database.

Why this exists
---------------
Neon's `neondb_owner` (like most managed-Postgres owner roles) carries the
BYPASSRLS attribute. A role with BYPASSRLS ignores every row-security policy,
and ALTER TABLE ... FORCE ROW LEVEL SECURITY does *not* override it. So the
policies from migration 0001 were structurally present and completely inert.

The fix is the separation real systems use anyway:

  neondb_owner   owns the schema, runs migrations, has BYPASSRLS
  meridian_app   serves requests, has no BYPASSRLS, is subject to the policies

The application must connect as `meridian_app` and nothing else. If it ever
connects as the owner, tenant isolation silently disappears — which is exactly
what the isolation test suite is there to catch.

Usage:  python scripts/create_app_role.py
"""

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

ROLE = "meridian_app"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


async def main() -> int:
    settings = get_settings()
    owner_url = settings.migration_database_url or settings.database_url
    # Alphanumeric only. Postgres DDL cannot take bind parameters, so this
    # value is inlined into the statement; restricting the charset to
    # [A-Za-z0-9] means it can contain no quote, backslash, or delimiter.
    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(40))
    assert password.isalnum()

    engine = create_async_engine(owner_url, connect_args={"statement_cache_size": 0})
    async with engine.begin() as c:
        me = (await c.execute(text("select rolbypassrls from pg_roles where rolname=current_user"))).scalar()
        if not me:
            print(f"refusing: connected as a role without BYPASSRLS; run this as the database owner")
            return 1

        exists = (await c.execute(
            text("select 1 from pg_roles where rolname=:r"), {"r": ROLE})).scalar()
        if exists:
            await c.execute(text(f"ALTER ROLE {ROLE} WITH PASSWORD '{password}'"))
            print(f"role {ROLE} already existed — password rotated")
        else:
            await c.execute(text(f"CREATE ROLE {ROLE} LOGIN PASSWORD '{password}'"))
            print(f"created role {ROLE}")

        # CREATE ROLE already defaults to NOSUPERUSER / NOBYPASSRLS, and this
        # connection is not a superuser so it may not issue a statement that
        # even mentions SUPERUSER. The attributes are therefore verified below
        # rather than asserted here.

        await c.execute(text(f"GRANT USAGE ON SCHEMA public TO {ROLE}"))
        await c.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}"))
        await c.execute(text(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {ROLE}"))
        # Tables created by future migrations must be reachable too.
        await c.execute(text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE}"))
        await c.execute(text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO {ROLE}"))
        # The app never migrates, so it must not touch the version table.
        await c.execute(text(f"REVOKE ALL ON alembic_version FROM {ROLE}"))

        check = (await c.execute(text(
            "select rolbypassrls, rolsuper from pg_roles where rolname=:r"), {"r": ROLE})).one()
        print(f"  BYPASSRLS={check[0]}  superuser={check[1]}")
        if check[0]:
            print("REFUSING: role still has BYPASSRLS")
            return 1

    await engine.dispose()

    # Rewrite .env: owner URL moves to MIGRATION_DATABASE_URL, app URL becomes DATABASE_URL.
    parts = urlsplit(owner_url.replace("postgresql+asyncpg://", "postgresql://"))
    host = parts.netloc.split("@", 1)[1]
    app_url = urlunsplit((parts.scheme, f"{ROLE}:{password}@{host}", parts.path, parts.query, ""))

    env = ENV_FILE.read_text()
    current_db = re.search(r"^DATABASE_URL=(.*)$", env, re.M)
    owner_plain = current_db.group(1) if current_db else owner_url

    if re.search(r"^MIGRATION_DATABASE_URL=", env, re.M):
        env = re.sub(r"^MIGRATION_DATABASE_URL=.*$", f"MIGRATION_DATABASE_URL={owner_plain}", env, flags=re.M)
    else:
        env = re.sub(r"^DATABASE_URL=.*$",
                     f"MIGRATION_DATABASE_URL={owner_plain}\nDATABASE_URL={app_url}", env, flags=re.M)
        ENV_FILE.write_text(env)
        print(f"\n.env updated:\n  MIGRATION_DATABASE_URL -> owner (runs alembic)\n  DATABASE_URL           -> {ROLE} (serves requests)")
        return 0

    env = re.sub(r"^DATABASE_URL=.*$", f"DATABASE_URL={app_url}", env, flags=re.M)
    ENV_FILE.write_text(env)
    print(f"\n.env updated: DATABASE_URL now uses {ROLE}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
