from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


# Load environment variables from app/backend/.env before other modules import settings
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    try:
        load_dotenv(env_path, override=False)
        logger.debug("Loaded environment variables from %s", env_path)
    except Exception:
        logger.exception("Failed to load .env file: %s", env_path)
else:
    logger.debug("No .env file found at %s; skipping", env_path)
