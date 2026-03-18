import json
import unittest

from app.utils.sql_parser import parse_input_json, parse_table_name

SAMPLE_SQL = (
    "CREATE TABLE `ai_media_task` (\n"
    "  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键ID',\n"
    "  `task_id` bigint(20) NOT NULL DEFAULT '0' COMMENT '任务ID'\n"
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI媒体任务表'"
)

SAMPLE_JSON = json.dumps(
    {
        "mysql_sql": SAMPLE_SQL,
        "day_or_hour": "天表",
        "product_line": "sfst",
    }
)


class TestParseTableName(unittest.TestCase):
    def test_normal_backtick(self):
        self.assertEqual(parse_table_name(SAMPLE_SQL), "ai_media_task")

    def test_normal_no_backtick(self):
        sql = "CREATE TABLE my_table (id int);"
        self.assertEqual(parse_table_name(sql), "my_table")

    def test_case_insensitive(self):
        sql = "create table User_Info (id int);"
        self.assertEqual(parse_table_name(sql), "User_Info")

    def test_invalid_sql_returns_none(self):
        self.assertIsNone(parse_table_name("SELECT * FROM foo"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_table_name(""))


class TestParseInputJson(unittest.TestCase):
    def test_valid_json(self):
        result = parse_input_json(SAMPLE_JSON)
        self.assertIsNotNone(result)
        self.assertEqual(result.day_or_hour, "天表")
        self.assertEqual(result.product_line, "sfst")
        self.assertEqual(result.mysql_sql, SAMPLE_SQL)

    def test_missing_mysql_sql(self):
        data = {"day_or_hour": "天表", "product_line": "sfst"}
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_missing_day_or_hour(self):
        data = {"mysql_sql": SAMPLE_SQL, "product_line": "sfst"}
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_missing_product_line(self):
        data = {"mysql_sql": SAMPLE_SQL, "day_or_hour": "天表"}
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_invalid_json_string(self):
        self.assertIsNone(parse_input_json("{not valid json}"))

    def test_empty_string_field(self):
        data = {"mysql_sql": "", "day_or_hour": "天表", "product_line": "sfst"}
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_valid_optional_fields(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "dw_layer": "ods",
            "table_format": "orc",
            "target_table_format": "hive",
            "operate_type": "新建表",
        }
        result = parse_input_json(json.dumps(data))
        self.assertIsNotNone(result)
        self.assertEqual(result.dw_layer, "ods")
        self.assertEqual(result.table_format, "orc")
        self.assertEqual(result.target_table_format, "hive")
        self.assertEqual(result.operate_type, "新建表")

    def test_dw_layer_invalid_value(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "dw_layer": "invalid",
        }
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_table_format_invalid_value(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "table_format": "parquet",
        }
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_target_table_format_invalid_value(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "target_table_format": "mysql",
        }
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_operate_type_invalid_value(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "operate_type": "删除表",
        }
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_optional_fields_empty_or_missing(self):
        result = parse_input_json(SAMPLE_JSON)
        self.assertIsNotNone(result)
        self.assertIsNone(result.dw_layer)
        self.assertIsNone(result.table_format)
        self.assertIsNone(result.target_table_format)
        self.assertIsNone(result.operate_type)

        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "dw_layer": "",
            "table_format": "",
        }
        result2 = parse_input_json(json.dumps(data))
        self.assertIsNotNone(result2)
        self.assertIsNone(result2.dw_layer)
        self.assertIsNone(result2.table_format)

    def test_dw_layer_valid_values(self):
        for val in ("ods", "mds", "sds"):
            data = {
                "mysql_sql": SAMPLE_SQL,
                "day_or_hour": "天表",
                "product_line": "sfst",
                "dw_layer": val,
            }
            result = parse_input_json(json.dumps(data))
            self.assertIsNotNone(result, f"dw_layer={val} should be valid")
            self.assertEqual(result.dw_layer, val)

    def test_table_format_valid_values(self):
        for val in ("orc", "rcfile", "txt"):
            data = {
                "mysql_sql": SAMPLE_SQL,
                "day_or_hour": "天表",
                "product_line": "sfst",
                "table_format": val,
            }
            result = parse_input_json(json.dumps(data))
            self.assertIsNotNone(result, f"table_format={val} should be valid")
            self.assertEqual(result.table_format, val)

    def test_target_table_format_valid_values(self):
        for val in ("hive", "clickhouse"):
            data = {
                "mysql_sql": SAMPLE_SQL,
                "day_or_hour": "天表",
                "product_line": "sfst",
                "target_table_format": val,
            }
            result = parse_input_json(json.dumps(data))
            self.assertIsNotNone(result, f"target_table_format={val} should be valid")
            self.assertEqual(result.target_table_format, val)

    def test_operate_type_valid_values(self):
        for val in ("新建表", "修改表"):
            data = {
                "mysql_sql": SAMPLE_SQL,
                "day_or_hour": "天表",
                "product_line": "sfst",
                "operate_type": val,
            }
            result = parse_input_json(json.dumps(data))
            self.assertIsNotNone(result, f"operate_type={val} should be valid")
            self.assertEqual(result.operate_type, val)


if __name__ == "__main__":
    unittest.main()
