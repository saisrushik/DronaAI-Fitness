"""Prints table privileges and row-level security status. Diagnostic helper."""

import asyncio

from sqlalchemy import text

from app.db.session import engine

QUERY = """
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
"""


async def main() -> None:
    async with engine.connect() as conn:
        count = await conn.scalar(text("SELECT count(*) FROM users"))
        print(f"users visible to this connection: {count}\n")
        for table, rls in (await conn.execute(text(QUERY))).all():
            print(f"  {table:22} row_level_security={rls}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
