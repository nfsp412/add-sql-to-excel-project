# add-sql-to-excel

> **弃用（v1.1.0）**：JSON → Hive/ClickHouse SQL 与 RPA 已合并至 [**create-table-project**](../create-table-project)，请使用  
> `create-table --json-file …` 或 `--json-string …`，无需再单独运行本工具。本目录仅作历史兼容与字段文档参考。

将 JSON 参数中的 MySQL 建表语句解析后，写入 Excel 表格的命令行工具。

## 功能说明

支持两类 JSON 输入（**顶层可为单对象或数组**）：

1. **新建表（含 `mysql_sql`）**  
   以下 **8 个字段均须存在且非空**，否则记录 WARNING 并跳过该项：  
   `mysql_sql`、`product_line`、`day_or_hour`、`dw_layer`、`table_format`、`target_table_format`、`operate_type`、`is_sharding`。  
   另可选：`table_comment`（不提供则从 `mysql_sql` 表级 COMMENT 解析）。  
   从 `mysql_sql` 解析 MySQL 表名；**新建表**在 `fields` 页写一行，建表语句列为完整 DDL。

2. **修改表（含 `new_fields` 数组）**  
   须包含：`table_name`、`operate_type`（须为 `修改表`）、`target_table_format`、`new_fields`（非空数组）。  
   每项为 `{ "field_name": "...", "field_type": "..." }`，`field_type` 可省略（默认 `string`）。  
   在 `tables` 页写一行（`hive表名` 与 `表名` 均填 `table_name`，便于下游直接使用 Hive 表名）；在 `fields` 页每个新字段一行，无建表语句。

- Excel 输出到按日期归档的目录（`create-table-output/YYYYMMDD/create_table_info.xlsx`）
- 每次运行会**覆盖整个 Excel 文件**（非追加），重跑不会产生重复数据
- 缺少必需字段或 SQL 解析失败时，记录日志并跳过该项；若全部跳过则退出码非 0
- SQL 中包含未转义的双引号时（如 `DEFAULT ""` 或 `COMMENT "xxx"`），自动将双引号替换为单引号后继续解析（MySQL 中两者等价）；**修改表 JSON 含数组，请尽量使用合法 JSON，自动修复能力有限**

### 与 create-table-project 的衔接

本工具生成的 Excel 是 [create-table-project](../create-table-project) 的输入。典型流程为：先运行 `add-sql-to-excel` 将 MySQL 建表语句写入 Excel，再运行 `create-table` 根据 Excel 生成 Hive/ClickHouse 建表 SQL。

### 字段映射

| Sheet  | 列名       | 来源                        | 可选值                    |
|--------|------------|-----------------------------|---------------------------|
| tables | 表名       | 从 `mysql_sql` 解析          | -                         |
| tables | 产品线     | `product_line`              | -                         |
| tables | 入仓方式   | `day_or_hour`               | 天表, 小时表              |
| tables | 表注释信息 | `table_comment`（可选，回退从 SQL COMMENT 解析） | -       |
| tables | 数仓分层   | 新建表必填 `dw_layer`；修改表为空 | ods, mds, sds             |
| tables | 建表格式   | 新建表必填 `table_format`；修改表为空 | orc, rcfile, text         |
| tables | 目标表类型 | 新建表必填 `target_table_format`；修改表必填 | hive, clickhouse          |
| tables | 操作类型   | `operate_type`               | 新建表, 修改表             |
| tables | hive表名   | 新建表：为空；**修改表**：与 `table_name` 相同 | - |
| tables | 是否分库分表 | 仅新建表：`is_sharding`（必填枚举）；修改表行为空 | 是, 否 |
| fields | 表名       | **新建表**：从 `mysql_sql` 解析；**修改表**：`table_name` | - |
| fields | 字段名 / 字段数据类型 | **新建表**：空；**修改表**：`new_fields` 每项一行 | - |
| fields | 操作类型   | 与 tables 一致               | 新建表, 修改表 |
| fields | 建表语句   | **新建表**：`mysql_sql` 原文；**修改表**：空 | - |
| fields | 字段注释   | **新建表**：空；**修改表**：可空 | - |

**JSON 路由**：若对象中**存在键** `new_fields`，则一律按**修改表**解析（不要求 `mysql_sql`）；否则若存在 `mysql_sql`，按**新建表**解析。若误将二者写在同一对象中，以 **`new_fields` 优先**（会走修改表分支）。

## 环境要求

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) 包管理工具

## 安装

```bash
# 克隆项目后进入目录
cd add-sql-to-excel-project

# 安装依赖
uv sync
```

说明：

- 这会根据 `pyproject.toml` 和 `uv.lock` 创建/复用本地虚拟环境（默认在 `.venv/`），并安装所需依赖。
- 如果尚未安装 `uv`，可参考官方安装文档（`https://docs.astral.sh/uv/`），或使用系统包管理器安装。

## 使用方法

### 安装为命令行工具使用

项目提供命令行入口：`add-sql-to-excel=app.main:main`（定义在 `pyproject.toml` 的 `[project.scripts]` 中）。

```bash
cd add-sql-to-excel-project

# 确保依赖已安装
uv sync

# 全局安装工具
uv tool install . --editable

# 若有报错：error: Querying Python at `.../bin/python3` failed with exit status signal: 9 (SIGKILL)
# 则执行： sudo codesign -s - -f /path/to/.../bin/python3

# 使用脚本入口运行（--file 需提供正确的相对/绝对路径）
uv run add-sql-to-excel --file ../create-table-output/20260318/input.json

# 调试模式
uv run add-sql-to-excel --file ../create-table-output/20260318/input.json --debug
```

> 若提示 `add-sql-to-excel: command not found`，请优先使用 `uv run add-sql-to-excel`；或者确认你已经在当前环境中安装了该项目（如使用传统 conda/venv，可在对应环境下执行 `pip install -e .`）。




### 通过命令行工具运行（推荐）

```bash
uv run add-sql-to-excel --json '{
  "mysql_sql": "CREATE TABLE `my_table` (id int) COMMENT='\''示例表'\''",
  "day_or_hour": "天表",
  "product_line": "sfst",
  "dw_layer": "ods",
  "table_format": "orc",
  "target_table_format": "hive",
  "operate_type": "新建表",
  "is_sharding": "否"
}'
```

### 通过 python 直接运行

```bash
uv run python app/main.py --json '{...}'
```

### 通过 python 模块化运行

```bash
uv run python -m app.main --json '{...}'
```

### 通过 JSON 文件输入

```bash
# --file 接受相对路径或绝对路径
# input.json 通常位于输出目录 create-table-output/YYYYMMDD/ 下
uv run add-sql-to-excel --file ../create-table-output/20260318/input.json
```

`input.json` 示例（含可选字段）：

```json
{
  "mysql_sql": "CREATE TABLE `ai_media_task` (\n  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',\n  `task_id` bigint(20) NOT NULL DEFAULT '0' COMMENT '任务ID'\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI媒体任务表'",
  "day_or_hour": "天表",
  "product_line": "sfst",
  "dw_layer": "ods",
  "table_format": "orc",
  "target_table_format": "hive",
  "operate_type": "新建表",
  "table_comment": "AI媒体任务表",
  "is_sharding": "否"
}
```

**新建表**：上述 8 项缺一不可（枚举须在允许值内）。`table_comment` 可选；未提供则从 `mysql_sql` 表级 `COMMENT` 解析；若 JSON 中显式写空字符串则仍回退解析 SQL。

**支持 JSON 数组格式**：输入可为数组 `[{...}, {...}]`，每项为一条「新建表」或「修改表」配置，将批量写入同一 Excel。单对象 `{...}` 仍兼容。

```json
[
  {
    "mysql_sql": "CREATE TABLE `table_a` (id int);",
    "day_or_hour": "天表",
    "product_line": "sfst",
    "dw_layer": "ods",
    "table_format": "orc",
    "target_table_format": "hive",
    "operate_type": "新建表",
    "is_sharding": "否"
  },
  {
    "table_name": "ods_ad_wax_table_b_day",
    "operate_type": "修改表",
    "target_table_format": "hive",
    "new_fields": [
      {"field_name": "new_col", "field_type": "bigint"}
    ]
  }
]
```

### 指定 Excel 输出路径

```bash
uv run add-sql-to-excel --file ../create-table-output/20260318/input.json --excel /path/to/output.xlsx
```

> 默认输出路径为项目父目录下的 `create-table-output/YYYYMMDD/create_table_info.xlsx`（按日期归档，覆盖写入）。

### 开启调试日志

```bash
uv run add-sql-to-excel --file ../create-table-output/20260318/input.json --debug
```

日志同时输出到控制台和 `create-table-output/YYYYMMDD/add_sql_to_excel.log` 文件。

## 运行测试

在项目根目录执行：

```bash
uv sync
uv run python -m unittest discover -s tests -v
```

一次性跑完全部用例（约 100+ 条）：

```bash
uv run python -m unittest discover -s tests -q
```

测试覆盖场景摘要：

- **SQL**：表名、表注释、分库分表后缀检测与剥离
- **新建表 JSON**：8 项必填、枚举校验、`table_comment` 可选与回退
- **修改表 JSON**：`new_fields`、`operate_type` 须为「修改表」、`field_type` 默认 `string`
- **双引号修复**：`mysql_sql` 内未转义双引号时的锚点修复（修改表带数组时建议直接提供合法 JSON）
- **Excel**：新建表一行 tables + 一行 fields；修改表一行 tables + 多行 fields；`hive表名` 与批量 `write_rows`
- **主流程**：`--json` / `--file`、数组多表、**新建 + 修改混排**、缺字段退出码、双引号 SQL 文件端到端、默认日期输出目录

## 项目结构

```
add-sql-to-excel-project/
├── pyproject.toml                # 项目依赖配置 & CLI 入口注册
├── README.md                     # 使用文档
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py                   # CLI 主入口（日期目录计算、参数解析）
│   ├── models.py                 # InputData（新建表）、ModifyTableInput / NewField（修改表）
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # 集中配置（输出目录、日志格式等）
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # 统一日志（控制台 + 文件双输出）
│       ├── sql_parser.py         # SQL 表名/表注释/分库分表解析 & JSON 输入解析
│       └── excel_writer.py       # Excel 覆盖写入逻辑
└── tests/
    ├── __init__.py
    ├── test_sql_parser.py        # SQL 解析单元测试
    ├── test_excel_writer.py      # Excel 写入单元测试
    ├── test_logger.py            # 日志配置单元测试
    └── test_main.py              # 主流程集成测试
```

## 异常处理

| 场景                      | 行为                       |
|---------------------------|----------------------------|
| SQL 含未转义双引号        | 自动替换为单引号后继续解析，记录 INFO 日志 |
| 顶层 JSON 解析失败且无法修复 | 记录 ERROR 日志并退出程序 |
| 数组某项解析失败（缺字段、非法值等） | 记录 WARNING 日志并跳过该项 |
| JSON 缺少必需字段         | 记录 WARNING 日志，跳过该项 |
| 可选字段值不在允许范围内  | 记录 WARNING 日志，跳过该项；若所有项均失败则程序退出 |
| SQL 中无法提取表名        | 记录 WARNING 日志，跳过该项 |
| Excel 文件已存在          | 覆盖写入，保证数据不重复    |
| 输出目录不存在            | 自动创建（含日期子目录）    |
