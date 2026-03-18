from dataclasses import dataclass


@dataclass
class InputData:
    mysql_sql: str
    day_or_hour: str
    product_line: str
    dw_layer: str | None = None           # ods | mds | sds
    table_format: str | None = None       # orc | rcfile | txt
    target_table_format: str | None = None  # hive | clickhouse
    operate_type: str | None = None       # 新建表 | 修改表
    table_comment: str | None = None      # 表注释（优先 JSON 字段，回退 SQL COMMENT）
