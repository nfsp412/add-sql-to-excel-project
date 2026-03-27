from dataclasses import dataclass, field


@dataclass
class NewField:
    """修改表场景下待新增的字段。"""

    field_name: str
    field_type: str


@dataclass
class ModifyTableInput:
    """修改表 JSON 解析结果（无 mysql_sql，写入多行 fields）。"""

    table_name: str
    target_table_format: str  # hive | clickhouse
    operate_type: str  # 修改表
    new_fields: list[NewField] = field(default_factory=list)


@dataclass
class InputData:
    mysql_sql: str
    day_or_hour: str
    product_line: str
    dw_layer: str | None = None           # ods | mds | sds
    table_format: str | None = None       # orc | rcfile | text
    target_table_format: str | None = None  # hive | clickhouse
    operate_type: str | None = None       # 新建表 | 修改表
    table_comment: str | None = None      # 表注释（优先 JSON 字段，回退 SQL COMMENT）
    is_sharding: str = "否"               # 是 | 否（优先 JSON 字段，回退表名模式检测）
