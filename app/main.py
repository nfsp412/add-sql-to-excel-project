import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.config.settings import EXCEL_FILENAME, OUTPUT_BASE_DIR
from app.utils.excel_writer import write_rows
from app.utils.logger import setup_logging
from app.utils.sql_parser import _try_repair_json, parse_input_dict

logger = logging.getLogger(__name__)


def build_parser(default_excel: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 JSON 参数中的 MySQL 建表语句解析后填充到 Excel 表中。"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--json",
        metavar="JSON_STRING",
        help="直接传入 JSON 字符串",
    )
    source.add_argument(
        "--file",
        metavar="PATH",
        type=Path,
        help="从 JSON 文件中读取输入",
    )
    parser.add_argument(
        "--excel",
        metavar="PATH",
        type=Path,
        default=default_excel,
        help=f"Excel 输出路径（默认: {default_excel}）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启 DEBUG 日志等级，输出更详细的调试信息",
    )
    return parser


def main() -> None:
    today = datetime.now().strftime("%Y%m%d")
    output_dir = OUTPUT_BASE_DIR / today
    output_dir.mkdir(parents=True, exist_ok=True)
    default_excel = output_dir / EXCEL_FILENAME

    parser = build_parser(default_excel)
    args = parser.parse_args()

    setup_logging(debug=args.debug, log_dir=output_dir)
    logger.info("add_sql_to_excel 脚本启动")

    if args.file:
        if not args.file.exists():
            logger.error("JSON 文件不存在: %s", args.file)
            sys.exit(1)
        json_str = args.file.read_text(encoding="utf-8")
    else:
        json_str = args.json

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        parsed = _try_repair_json(json_str)
        if parsed is None:
            logger.error("JSON 解析失败且自动修复未成功，程序退出。")
            sys.exit(1)
        logger.info("已自动修复 JSON（SQL 中的双引号已替换为单引号）")

    if isinstance(parsed, dict):
        items = [parsed]
    elif isinstance(parsed, list):
        items = parsed
    else:
        logger.error("输入格式错误，应为 JSON 对象或数组")
        sys.exit(1)

    data_list: list = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logger.warning("第 %d 项不是对象，跳过", i + 1)
            continue
        data = parse_input_dict(item)
        if data:
            data_list.append(data)

    if not data_list:
        logger.error("没有可写入的数据，程序退出。")
        sys.exit(1)

    write_rows(args.excel, data_list)


if __name__ == "__main__":
    main()
