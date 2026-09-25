import logging
import sys
from collections.abc import Iterator
from pathlib import Path

LOGGER_NAME = "geo_intelligence"
LOG_FORMAT = "%(asctime)s - %(levelname)s - [GEO-INT] - %(message)s"


class FileAuditLog:
    """Audit trail persisted to a log file and mirrored to stdout (visible in `docker logs`)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(LOG_FORMAT)
        file_handler = logging.FileHandler(self._path, mode="a", encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stdout)
        for handler in (file_handler, console_handler):
            handler.setFormatter(formatter)

        self._logger = logging.getLogger(LOGGER_NAME)
        self._logger.setLevel(logging.INFO)
        self._remove_handlers()
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        self.info("Audit system initialized and logging started.")

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)

    def entries(self) -> Iterator[str] | None:
        if not self._path.exists():
            return None
        return self._read_lines()

    def close(self) -> None:
        self._remove_handlers()

    def _read_lines(self) -> Iterator[str]:
        with self._path.open("r", encoding="utf-8") as f:
            yield from f

    def _remove_handlers(self) -> None:
        # The logger is process-wide: drop handlers left by a previous instance (e.g. in tests).
        for handler in list(self._logger.handlers):
            self._logger.removeHandler(handler)
            handler.close()
