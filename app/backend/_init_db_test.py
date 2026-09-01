import asyncio
import logging
import os
import traceback

from services.database import initialize_database, close_database


async def main():
    logging.basicConfig(level=logging.INFO)
    # Ensure bootstrap_env (loads .env) is executed
    import core.bootstrap_env  # noqa: F401

    try:
        await initialize_database()
        print("DB_INIT_OK")
    except Exception:
        print("DB_INIT_FAILED")
        traceback.print_exc()
    finally:
        try:
            await close_database()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
