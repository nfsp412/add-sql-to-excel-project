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
IS_SHARDING_VALUES = frozenset(("是", "否"))


_ALL_KEYS = (
    "mysql_sql", "day_or_hour", "product_line",
    "dw_layer", "table_format", "target_table_format", "operate_type",
    "table_comment", "is_sharding",
)


def _try_repair_json(raw: str) -> dict | None:
    """当 json.loads 因 SQL 中未转义的双引号失败时，利用已知 key 名作为锚点提取各字段值。

    提取到的 value 中的双引号会被替换为单引号（MySQL 中两者等价）。
    """
    key_pattern = "|".join(re.escape(k) for k in _ALL_KEYS)
    anchor_re = re.compile(rf'"({key_pattern})"\s*:\s*"')

    matches = list(anchor_re.finditer(raw))
    if not matches:
        return None

    result: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        val_start = m.end()

        if i + 1 < len(matches):
            segment = raw[val_start:matches[i + 1].start()]
            end = re.search(r'"\s*,\s*$', segment)
            if not end:
                return None
            value = segment[:end.start()]
        else:
            segment = raw[val_start:]
            end = re.search(r'"\s*}\s*$', segment)
            if not end:
                return None
            value = segment[:end.start()]

        result[key] = value.replace('"', "'")

    return result


def _validate_optional_field(value: str | None, allowed: frozenset[str], field_name: str) -> bool:
    """若字段有值但不在允许枚举内，返回 False；否则返回 True。"""
    if not value:
        return True
    if value in allowed:
        return True
    logger.warning("可选字段 %s 非法值 '%s'，允许值: %s，跳过本次处理", field_name, value, sorted(allowed))
    return False


def parse_table_comment(sql: str) -> str | None:
    """从 MySQL DDL 的表级属性中提取 COMMENT，仅匹配 ')' 之后的部分以避免误取列注释。"""
    paren_pos = sql.rfind(")")
    if paren_pos == -1:
        return None
    suffix = sql[paren_pos + 1:]
    match = re.search(r"COMMENT\s*=?\s*['\"](.+?)['\"]", suffix, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def detect_sharding(table_name: str) -> str:
    """检测表名是否以 _数字 结尾，判断是否为分库分表。"""
    return "是" if re.search(r"_\d+$", table_name) else "否"


def strip_sharding_suffix(table_name: str) -> str:
    """当表名为分库分表时，去除末尾的 _数字 后缀。"""
    return re.sub(r"_\d+$", "", table_name)


def parse_table_name(sql: str) -> str | None:
    """从 MySQL DDL 中提取表名，失败时返回 None。"""
    match = re.search(r"CREATE\s+TABLE\s+`?(\w+)`?", sql, re.IGNORECASE)
    if match:
        return match.group(1)
    logger.warning("无法从 SQL 中解析表名，SQL 片段: %.100s", sql)
    return None


def parse_input_dict(data: dict) -> InputData | None:
    """解析 dict 为 InputData，缺少必需字段时记录日志并返回 None。"""
    missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
    if missing:
        logger.warning("JSON 缺少必需字段: %s，跳过本次处理", missing)
        return None

    dw_layer = data.get("dw_layer") or None
    table_format = data.get("table_format") or None
    target_table_format = data.get("target_table_format") or None
    operate_type = data.get("operate_type") or None
    table_comment = data.get("table_comment") or None
    is_sharding = data.get("is_sharding") or None

    if not _validate_optional_field(dw_layer, DW_LAYER_VALUES, "dw_layer"):
        return None
    if not _validate_optional_field(table_format, TABLE_FORMAT_VALUES, "table_format"):
        return None
    if not _validate_optional_field(target_table_format, TARGET_TABLE_FORMAT_VALUES, "target_table_format"):
        return None
    if not _validate_optional_field(operate_type, OPERATE_TYPE_VALUES, "operate_type"):
        return None
    if not _validate_optional_field(is_sharding, IS_SHARDING_VALUES, "is_sharding"):
        return None

    if not table_comment:
        table_comment = parse_table_comment(data["mysql_sql"])

    if not is_sharding:
        table_name = parse_table_name(data["mysql_sql"])
        is_sharding = detect_sharding(table_name) if table_name else "否"

    return InputData(
        mysql_sql=data["mysql_sql"],
        day_or_hour=data["day_or_hour"],
        product_line=data["product_line"],
        dw_layer=dw_layer,
        table_format=table_format,
        target_table_format=target_table_format,
        operate_type=operate_type,
        table_comment=table_comment,
        is_sharding=is_sharding,
    )


def parse_input_json(json_str: str) -> InputData | None:
    """解析 JSON 字符串为 InputData，缺少必需字段时记录日志并返回 None。"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        data = _try_repair_json(json_str)
        if data is None:
            logger.warning("JSON 解析失败且自动修复未成功，请检查输入格式")
            return None
        logger.info("已自动修复 JSON（SQL 中的双引号已替换为单引号）")

    if not isinstance(data, dict):
        return None
    return parse_input_dict(data)
