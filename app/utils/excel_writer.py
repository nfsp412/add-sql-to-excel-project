import logging
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.models import InputData
from app.utils.sql_parser import parse_table_name

logger = logging.getLogger(__name__)

TABLES_HEADERS = [
    "表名", "产品线", "入仓方式", "表注释信息",
    "数仓分层", "建表格式", "目标表类型", "操作类型", "hive表名",
]

FIELDS_HEADERS = [
    "表名", "字段名", "字段数据类型", "字段注释", "操作类型", "建表语句",
]


def _create_workbook() -> Workbook:
    wb = Workbook()
    tables_ws: Worksheet = wb.active
    tables_ws.title = "tables"
    tables_ws.append(TABLES_HEADERS)

    fields_ws: Worksheet = wb.create_sheet("fields")
    fields_ws.append(FIELDS_HEADERS)

    return wb


def write_row(excel_path: str | Path, data: InputData) -> None:
    """将 InputData 数据写入 Excel 的 tables 和 fields 两个 Sheet（覆盖模式）。"""
    table_name = parse_table_name(data.mysql_sql)
    if table_name is None:
        logger.warning("SQL 解析失败，跳过写入。")
        return

    p = Path(excel_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    wb = _create_workbook()

    tables_ws: Worksheet = wb["tables"]
    tables_ws.append([
        table_name,
        data.product_line,
        data.day_or_hour,
        None,
        data.dw_layer,
        data.table_format,
        data.target_table_format,
        data.operate_type,
        None,
    ])

    fields_ws: Worksheet = wb["fields"]
    fields_ws.append([
        table_name,
        None,
        None,
        None,
        data.operate_type,
        data.mysql_sql,
    ])

    wb.save(p)
    logger.info("已写入表 '%s' 到 %s", table_name, p)
