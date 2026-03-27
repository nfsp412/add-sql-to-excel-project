import json
import logging
import re
from typing import Union

from app.models import InputData, ModifyTableInput, NewField

logger = logging.getLogger(__name__)

# 新建表（mysql_sql）路径：以下键均须存在且非空（table_comment 仍可选）
CREATE_TABLE_REQUIRED_FIELDS = (
    "mysql_sql",
    "product_line",
    "day_or_hour",
    "dw_layer",
    "table_format",
    "target_table_format",
    "operate_type",
    "is_sharding",
)

DW_LAYER_VALUES = frozenset(("ods", "mds", "sds"))
TABLE_FORMAT_VALUES = frozenset(("orc", "rcfile", "text"))
TARGET_TABLE_FORMAT_VALUES = frozenset(("hive", "clickhouse"))
OPERATE_TYPE_VALUES = frozenset(("新建表", "修改表"))
IS_SHARDING_VALUES = frozenset(("是", "否"))

_ALL_KEYS = (
    "mysql_sql", "day_or_hour", "product_line",
    "dw_layer", "table_format", "target_table_format", "operate_type",
    "table_comment", "is_sharding", "table_name",
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


def _parse_modify_table_dict(data: dict) -> ModifyTableInput | None:
    """解析修改表 JSON（table_name + new_fields + …）。"""
    required = ("table_name", "operate_type", "target_table_format", "new_fields")
    missing = [f for f in required if f not in data or data.get(f) in (None, "", [])]
    if missing:
        logger.warning("修改表 JSON 缺少必需字段或为空: %s，跳过本次处理", missing)
        return None

    table_name = str(data["table_name"]).strip()
    if not table_name:
        logger.warning("修改表 JSON table_name 为空，跳过本次处理")
        return None

    operate_type = str(data["operate_type"]).strip()
    if operate_type != "修改表":
        logger.warning("修改表 JSON operate_type 须为「修改表」，当前为 '%s'，跳过本次处理", operate_type)
        return None

    target_table_format = str(data["target_table_format"]).strip()
    if not _validate_optional_field(target_table_format, TARGET_TABLE_FORMAT_VALUES, "target_table_format"):
        return None

    raw_fields = data["new_fields"]
    if not isinstance(raw_fields, list) or len(raw_fields) == 0:
        logger.warning("修改表 JSON new_fields 须为非空数组，跳过本次处理")
        return None

    new_fields: list[NewField] = []
    for i, item in enumerate(raw_fields):
        if not isinstance(item, dict):
            logger.warning("修改表 new_fields[%d] 不是对象，跳过本次处理", i)
            return None
        fn = item.get("field_name")
        if not fn or not str(fn).strip():
            logger.warning("修改表 new_fields[%d] 缺少 field_name，跳过本次处理", i)
            return None
        ft_raw = item.get("field_type")
        ft = "string" if ft_raw in (None, "") else str(ft_raw).strip()
        new_fields.append(NewField(field_name=str(fn).strip(), field_type=ft))

    return ModifyTableInput(
        table_name=table_name,
        target_table_format=target_table_format,
        operate_type=operate_type,
        new_fields=new_fields,
    )


def _parse_create_table_dict(data: dict) -> InputData | None:
    """解析新建表 JSON（mysql_sql），八项必填。"""
    missing = [f for f in CREATE_TABLE_REQUIRED_FIELDS if not data.get(f)]
    if missing:
        logger.warning("JSON 缺少必需字段: %s，跳过本次处理", missing)
        return None

    dw_layer = str(data["dw_layer"]).strip()
    table_format = str(data["table_format"]).strip()
    target_table_format = str(data["target_table_format"]).strip()
    operate_type = str(data["operate_type"]).strip()
    is_sharding = str(data["is_sharding"]).strip()

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

    table_comment = data.get("table_comment")
    if table_comment is not None:
        table_comment = str(table_comment).strip() or None
    if not table_comment:
        table_comment = parse_table_comment(data["mysql_sql"])

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


def parse_input_dict(data: dict) -> Union[InputData, ModifyTableInput, None]:
    """解析 dict：含 new_fields 数组则走修改表；否则含 mysql_sql 则走新建表。"""
    if "new_fields" in data:
        return _parse_modify_table_dict(data)
    if "mysql_sql" in data:
        return _parse_create_table_dict(data)
    logger.warning("JSON 既不是修改表（无 new_fields）也不是新建表（无 mysql_sql），跳过本次处理")
    return None


def parse_input_json(json_str: str) -> Union[InputData, ModifyTableInput, None]:
    """解析 JSON 字符串为新建表 InputData 或修改表 ModifyTableInput。"""
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
