import logging.config
import datetime as dt
import logging

from cs_tools.cli.ux import rich_console
from cs_tools.const import APP_DIR


def _monkeypatch_logging_trace():
    """
    """
    # HTTPX defines the TRACE loglevel. (link: https://github.com/encode/httpx/blob/master/httpx/_utils.py#L232)
    # 40 --> ERROR
    # 30 --> WARNING
    # 20 --> INFO
    # 10 --> DEBUG
    #  5 --> TRACE
    #
    # We just need to monkeypatch it into the logging environment.
    def _trace_log_level(self, message, *args, **kwargs):
        if self.isEnabledFor(5):
            self._log(5, message, args, **kwargs)

    def _log_to_root(message, *args, **kwargs):
        logging.log(5, message, *args, **kwargs)

    logging.getLoggerClass().trace = _trace_log_level
    logging.trace = _log_to_root


def _rotate_logs(n_files_to_keep: int) -> None:
    logs_dir = APP_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    lifo = sorted(logs_dir.iterdir(), reverse=True)

    # keep only the last 25 logfiles
    for idx, log in enumerate(lifo):
        if idx > n_files_to_keep:
            log.unlink()


def _setup_logging() -> None:
    _monkeypatch_logging_trace()
    _rotate_logs(n_files_to_keep=25)

    logging.getLogger("httpx").setLevel("INFO")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "shell": {
                "format": "%(message)s",
            },
            "verbose": {
                "format": "[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s",
            },
        },
        "handlers": {},
        "loggers": {
            # as of httpx == 0.24.0 , we're REALLY noisy
            "httpx": {
                "handlers": [],
                "level": "WARNING",
            },
        },
        "root": {
            "handlers": [],
            "level": "DEBUG",
        },
    }

    config["root"]["handlers"].append("to_console")
    config["handlers"]["to_console"] = {
        "formatter": "shell",
        "level": "INFO",
        "class": "rich.logging.RichHandler",
        # rich.__init__ params...
        "console": rich_console,
        "show_level": True,
        "rich_tracebacks": True,
        "markup": True,
        "log_time_format": "[%X]",
    }

    logs_dir = APP_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().strftime("%Y-%m-%dT%H_%M_%S")

    config["root"]["handlers"].append("to_file")
    config["handlers"]["to_file"] = {
        "formatter": "verbose",
        "level": "DEBUG",
        "class": "logging.FileHandler",
        "filename": f"{logs_dir}/{now}.log",
        "mode": "w",
        "encoding": "utf-8",
        "delay": True,
    }

    logging.config.dictConfig(config)