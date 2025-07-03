import logging.config
from datetime import datetime
from typing import Any
import structlog

#
# --- helpers --------------------------------------------------------------
#
def _add_timestamp(_, __, event: dict[str, Any]):
    event["timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return event


#
# --- public API -----------------------------------------------------------
#
def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"plain": {"format": "%(message)s"}},
            "handlers": {
                "default": {"class": "logging.StreamHandler", "formatter": "plain"}
            },
            "loggers": {"": {"handlers": ["default"], "level": level}},
        }
    )

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        processors=[
            structlog.processors.CallsiteParameterAdder(
                [structlog.processors.CallsiteParameter.FILENAME,
                 structlog.processors.CallsiteParameter.LINENO]
            ),
            _add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )
