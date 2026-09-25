import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_AUDIT_LOG_PATH = Path("data") / "operation.log"


@dataclass(frozen=True)
class Settings:
    command_key: str | None
    audit_log_path: Path = DEFAULT_AUDIT_LOG_PATH

    @classmethod
    def from_env(cls) -> "Settings":
        """Read settings from the environment, loading a `.env` file if present."""
        load_dotenv()
        return cls(command_key=os.getenv("API_KEY_COMMAND"))
