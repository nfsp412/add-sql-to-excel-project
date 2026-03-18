import json
import logging
import re

from app.models import InputData

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("mysql_sql", "day_or_hour", "product_line")

DW_LAYER_VALUES = frozenset(("ods", "mds", "sds"))
TABLE_FORMAT_VALUES = frozenset(("orc", "rcfile", "txt"))
TARGET_TABLE_FORMAT_VALUES = frozenset(("hive", "clickhouse"))
OPERATE_TYPE_VALUES = frozenset(("新建表", "修改表"))


def _validate_optional_field(value: str | None, allowed: frozenset[str], field_name: str) -> bool:
    """若字段有值但不在允许枚举内，返回 False；否则返回 True。"""
    if not value:
        return True
    if value in allowed:
        return True
    logger.warning("可选字段 %s 非法值 '%s'，允许值: %s，跳过本次处理", field_name, value, sorted(allowed))
    return False


def parse_table_name(sql: str) -> str | None:
    """从 MySQL DDL 中提取表名，失败时返回 None。"""
    match = re.search(r"CREATE\s+TABLE\s+`?(\w+)`?", sql, re.IGNORECASE)
    if match:
        return match.group(1)
    logger.warning("无法从 SQL 中解析表名，SQL 片段: %.100s", sql)
    return None


def parse_input_json(json_str: str) -> InputData | None:
    """解析 JSON 字符串为 InputData，缺少必需字段时记录日志并返回 None。"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning("JSON 解析失败: %s", exc)
        return None

    missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
    if missing:
        logger.warning("JSON 缺少必需字段: %s，跳过本次处理", missing)
        return None

    dw_layer = data.get("dw_layer") or None
    table_format = data.get("table_format") or None
    target_table_format = data.get("target_table_format") or None
    operate_type = data.get("operate_type") or None

    if not _validate_optional_field(dw_layer, DW_LAYER_VALUES, "dw_layer"):
        return None
    if not _validate_optional_field(table_format, TABLE_FORMAT_VALUES, "table_format"):
        return None
    if not _validate_optional_field(target_table_format, TARGET_TABLE_FORMAT_VALUES, "target_table_format"):
        return None
    if not _validate_optional_field(operate_type, OPERATE_TYPE_VALUES, "operate_type"):
        return None

    return InputData(
        mysql_sql=data["mysql_sql"],
        day_or_hour=data["day_or_hour"],
        product_line=data["product_line"],
        dw_layer=dw_layer,
        table_format=table_format,
        target_table_format=target_table_format,
        operate_type=operate_type,
    )
