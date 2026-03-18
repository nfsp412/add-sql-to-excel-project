# add-sql-to-excel

将 JSON 参数中的 MySQL 建表语句解析后，写入 Excel 表格的命令行工具。

## 功能说明

- 接收包含 `mysql_sql`、`day_or_hour`、`product_line` 三个必需字段的 JSON 输入
- 支持 4 个可选字段：`dw_layer`、`table_format`、`target_table_format`、`operate_type`
- 从 `mysql_sql` 中解析 MySQL 表名
- 将解析结果写入 Excel 的 `tables` 和 `fields` 两个 Sheet
- Excel 输出到按日期归档的目录（`create-table-output/YYYYMMDD/create_table_info.xlsx`）
- 采用**覆盖写入**模式，重跑脚本不会产生重复数据
- 缺少必需字段或 SQL 解析失败时，记录日志并跳过，不终止程序

### 字段映射

| Sheet  | 列名       | 来源                        | 可选值                    |
|--------|------------|-----------------------------|---------------------------|
| tables | 表名       | 从 `mysql_sql` 解析          | -                         |
| tables | 产品线     | `product_line`              | -                         |
| tables | 入仓方式   | `day_or_hour`               | -                         |
| tables | 数仓分层   | `dw_layer`（可选）           | ods, mds, sds             |
| tables | 建表格式   | `table_format`（可选）       | orc, rcfile, txt          |
| tables | 目标表类型 | `target_table_format`（可选）| hive, clickhouse          |
| tables | 操作类型   | `operate_type`（可选）       | 新建表, 修改表             |
| tables | 其他列     | 置空                         | -                         |
| fields | 表名       | 从 `mysql_sql` 解析          | -                         |
| fields | 操作类型   | `operate_type`（可选，与 tables 一致） | 新建表, 修改表 |
| fields | 建表语句   | `mysql_sql` 原文（不做修改）  | -                         |
| fields | 其他列     | 置空                         | -                         |

## 环境要求

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) 包管理工具

## 安装

```bash
# 克隆项目后进入目录
cd add-sql-to-excel-project

# 安装依赖
uv sync
```

## 使用方法

### 通过命令行工具运行（推荐）

```bash
uv run add-sql-to-excel --json '{
  "mysql_sql": "CREATE TABLE `my_table` (id int) COMMENT='\''示例表'\''",
  "day_or_hour": "天表",
  "product_line": "sfst"
}'
```

### 通过 python 直接运行

```bash
uv run python app/main.py --json '{...}'
```

### 通过 JSON 文件输入

```bash
uv run add-sql-to-excel --file input.json
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
  "operate_type": "新建表"
}
```

可选字段均可省略；若提供则必须在允许值范围内，否则记录 WARNING 并跳过。

### 指定 Excel 输出路径

```bash
uv run add-sql-to-excel --file input.json --excel /path/to/output.xlsx
```

> 默认输出路径为同级目录 `create-table-output/YYYYMMDD/create_table_info.xlsx`（按日期归档，覆盖写入）。

### 开启调试日志

```bash
uv run add-sql-to-excel --file input.json --debug
```

日志同时输出到控制台和 `logs/add_sql_to_excel.log` 文件。

## 运行测试

```bash
uv run python -m unittest discover -v tests
```

测试覆盖场景：

- SQL 表名解析（正常 / 无反引号 / 大小写不敏感 / 解析失败 / 空字符串）
- JSON 解析（有效输入 / 缺少各必需字段 / JSON 格式错误 / 字段值为空 / 可选字段枚举校验）
- Excel 写入（新建文件 / 正确列头 / 覆盖写入 / SQL 原文保留 / 解析失败跳过 / 可选字段写入 / 操作类型两页一致性 / 自动创建父目录）
- 主流程（`--json` 参数 / `--file` 参数 / 输入解析失败退出 / JSON 文件不存在退出）

## 项目结构

```
add-sql-to-excel-project/
├── pyproject.toml                # 项目依赖配置 & CLI 入口注册
├── .python-version               # Python 版本锁定
├── README.md                     # 使用文档
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py                   # CLI 主入口（日期目录计算、参数解析）
│   ├── models.py                 # InputData 数据类
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # 集中配置（输出目录、日志格式等）
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # 统一日志（控制台 + 文件双输出）
│       ├── sql_parser.py         # SQL 表名解析 & JSON 输入解析
│       └── excel_writer.py       # Excel 覆盖写入逻辑
├── logs/                         # 日志输出目录
└── tests/
    ├── __init__.py
    ├── test_sql_parser.py        # SQL 解析单元测试
    ├── test_excel_writer.py      # Excel 写入单元测试
    └── test_main.py              # 主流程集成测试
```

## 异常处理

| 场景                      | 行为                       |
|---------------------------|----------------------------|
| JSON 格式非法             | 记录 WARNING 日志，跳过     |
| JSON 缺少必需字段         | 记录 WARNING 日志，跳过     |
| 可选字段值不在允许范围内  | 记录 WARNING 日志，跳过     |
| SQL 中无法提取表名        | 记录 WARNING 日志，跳过     |
| Excel 文件已存在          | 覆盖写入，保证数据不重复    |
| 输出目录不存在            | 自动创建（含日期子目录）    |
