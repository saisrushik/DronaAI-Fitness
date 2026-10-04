"""Creates a least-privilege database role for the application.

The app connects as this role (DML only). Alembic keeps using the owner account for DDL.
Run once with: python -m scripts.create_app_role
"""

import asyncio
import re
import secrets

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

ROLE = "fitness_app"

# Supabase enables row-level security on every table. Those policies exist to guard its public
# Data API roles; our backend does its own authorization and needs to see all rows, so it
# bypasses RLS while still being unable to change the schema.
# The app never deletes rows, so leaked app credentials can't be used to wipe data either.
STATEMENTS = [
    "ALTER ROLE {role} BYPASSRLS",
    "GRANT USAGE ON SCHEMA public TO {role}",
    "REVOKE DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM {role}",
    "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {role}",
    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE DELETE, TRUNCATE ON TABLES FROM {role}",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO {role}",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {role}",
]


async def main() -> None:
    # Postgres forbids bind parameters in CREATE ROLE, so the password is inlined.
    # Restrict it to characters that need no SQL or URL escaping.
    password = re.sub(r"[^A-Za-z0-9]", "", secrets.token_urlsafe(48))[:32]

    async with engine.begin() as conn:
        exists = await conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": ROLE})
        if exists:
            await conn.execute(text(f"ALTER ROLE {ROLE} WITH LOGIN PASSWORD '{password}'"))
            print(f"Role {ROLE} already existed - password rotated.")
        else:
            await conn.execute(text(f"CREATE ROLE {ROLE} WITH LOGIN PASSWORD '{password}'"))
            print(f"Role {ROLE} created.")

        for statement in STATEMENTS:
            await conn.execute(text(statement.format(role=ROLE)))

    # Rebuild the connection string from the owner URL, swapping in the new credentials.
    # Supabase's pooler expects the username as "<dbuser>.<project-ref>".
    credentials, host = settings.DATABASE_URL.split("://", 1)[1].split("@", 1)
    owner_user = credentials.split(":", 1)[0]
    user = f"{ROLE}.{owner_user.split('.', 1)[1]}" if "." in owner_user else ROLE
    app_url = f"postgresql+asyncpg://{user}:{password}@{host}"

    print("\nGrants applied. Put this in your .env as DATABASE_URL:\n")
    print(app_url)
    print(
        "\nKeep DATABASE_URL_SYNC pointing at the owner account - Alembic needs DDL rights."
    )


if __name__ == "__main__":
    asyncio.run(main())
