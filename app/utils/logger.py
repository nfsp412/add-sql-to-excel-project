"""日志工具模块"""
import logging
import os
from pathlib import Path

from app.config.settings import LOG_DIR, LOG_DATE_FORMAT, LOG_FORMAT


def setup_logging(debug: bool = False) -> None:
    """
    配置统一的日志格式，支持控制台 + 文件双输出。
    """
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(LOG_DIR, "add_sql_to_excel.log"),
                encoding="utf-8",
            ),
        ],
    )
