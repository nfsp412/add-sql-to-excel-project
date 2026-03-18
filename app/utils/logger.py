"""日志工具模块"""
import logging
from pathlib import Path

from app.config.settings import LOG_DATE_FORMAT, LOG_DIR, LOG_FORMAT


def setup_logging(debug: bool = False, log_dir: str | Path | None = None) -> None:
    """
    配置统一的日志格式，支持控制台 + 文件双输出。
    当 log_dir 有值时，日志文件写入 log_dir/add_sql_to_excel.log；否则使用项目内 LOG_DIR。
    """
    file_log_dir = Path(log_dir) if log_dir else Path(LOG_DIR)
    file_log_dir.mkdir(parents=True, exist_ok=True)
    log_file = file_log_dir / "add_sql_to_excel.log"

    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )
