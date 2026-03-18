import json
import unittest

from app.utils.sql_parser import detect_sharding, parse_input_json, parse_table_comment, parse_table_name

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


class TestParseTableComment(unittest.TestCase):
    def test_single_quote_with_equals(self):
        sql = "CREATE TABLE `t` (`id` int) ENGINE=InnoDB COMMENT='表注释'"
        self.assertEqual(parse_table_comment(sql), "表注释")

    def test_single_quote_without_equals(self):
        sql = "CREATE TABLE `t` (`id` int) ENGINE=InnoDB COMMENT '表注释'"
        self.assertEqual(parse_table_comment(sql), "表注释")

    def test_double_quote_with_equals(self):
        sql = 'CREATE TABLE `t` (`id` int) ENGINE=InnoDB COMMENT="表注释"'
        self.assertEqual(parse_table_comment(sql), "表注释")

    def test_double_quote_without_equals(self):
        sql = 'CREATE TABLE `t` (`id` int) ENGINE=InnoDB COMMENT "表注释"'
        self.assertEqual(parse_table_comment(sql), "表注释")

    def test_equals_with_spaces(self):
        sql = "CREATE TABLE `t` (`id` int) ENGINE=InnoDB COMMENT = '表注释'"
        self.assertEqual(parse_table_comment(sql), "表注释")

    def test_no_table_comment(self):
        sql = "CREATE TABLE `t` (`id` int COMMENT '列注释') ENGINE=InnoDB"
        self.assertIsNone(parse_table_comment(sql))

    def test_no_closing_paren(self):
        sql = "CREATE TABLE `t` COMMENT='xxx'"
        self.assertIsNone(parse_table_comment(sql))

    def test_multiline_sql(self):
        self.assertEqual(parse_table_comment(SAMPLE_SQL), "AI媒体任务表")

    def test_case_insensitive(self):
        sql = "CREATE TABLE `t` (`id` int) ENGINE=InnoDB comment='小写注释'"
        self.assertEqual(parse_table_comment(sql), "小写注释")

    def test_column_comment_not_captured(self):
        sql = (
            "CREATE TABLE `t` (\n"
            "  `name` varchar(64) COMMENT '用户名'\n"
            ") ENGINE=InnoDB"
        )
        self.assertIsNone(parse_table_comment(sql))


class TestDetectSharding(unittest.TestCase):
    def test_ends_with_single_digit(self):
        self.assertEqual(detect_sharding("order_0"), "是")

    def test_ends_with_multiple_digits(self):
        self.assertEqual(detect_sharding("order_00"), "是")
        self.assertEqual(detect_sharding("user_info_128"), "是")

    def test_ends_with_letters(self):
        self.assertEqual(detect_sharding("order_abc"), "否")

    def test_no_underscore_suffix(self):
        self.assertEqual(detect_sharding("order"), "否")

    def test_ends_with_underscore_only(self):
        self.assertEqual(detect_sharding("order_"), "否")

    def test_normal_table_name(self):
        self.assertEqual(detect_sharding("ai_media_task"), "否")

    def test_digit_in_middle_not_at_end(self):
        self.assertEqual(detect_sharding("t2_info"), "否")


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

    def test_table_comment_from_json(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "table_comment": "自定义注释",
        }
        result = parse_input_json(json.dumps(data))
        self.assertIsNotNone(result)
        self.assertEqual(result.table_comment, "自定义注释")

    def test_table_comment_fallback_from_sql(self):
        result = parse_input_json(SAMPLE_JSON)
        self.assertIsNotNone(result)
        self.assertEqual(result.table_comment, "AI媒体任务表")

    def test_table_comment_json_takes_priority_over_sql(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "table_comment": "JSON优先注释",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.table_comment, "JSON优先注释")

    def test_table_comment_empty_string_falls_back_to_sql(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "table_comment": "",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.table_comment, "AI媒体任务表")

    def test_table_comment_none_when_sql_has_no_comment(self):
        sql_no_comment = "CREATE TABLE `t` (`id` int) ENGINE=InnoDB"
        data = {
            "mysql_sql": sql_no_comment,
            "day_or_hour": "天表",
            "product_line": "sfst",
        }
        result = parse_input_json(json.dumps(data))
        self.assertIsNotNone(result)
        self.assertIsNone(result.table_comment)

    def test_is_sharding_from_json_yes(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "is_sharding": "是",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.is_sharding, "是")

    def test_is_sharding_from_json_no(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "is_sharding": "否",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.is_sharding, "否")

    def test_is_sharding_json_no_overrides_sql_detection(self):
        sharding_sql = "CREATE TABLE `order_0` (`id` int) ENGINE=InnoDB"
        data = {
            "mysql_sql": sharding_sql,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "is_sharding": "否",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.is_sharding, "否")

    def test_is_sharding_auto_detect_yes(self):
        sharding_sql = "CREATE TABLE `order_0` (`id` int) ENGINE=InnoDB"
        data = {
            "mysql_sql": sharding_sql,
            "day_or_hour": "天表",
            "product_line": "sfst",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.is_sharding, "是")

    def test_is_sharding_auto_detect_no(self):
        result = parse_input_json(SAMPLE_JSON)
        self.assertEqual(result.is_sharding, "否")

    def test_is_sharding_invalid_value(self):
        data = {
            "mysql_sql": SAMPLE_SQL,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "is_sharding": "maybe",
        }
        self.assertIsNone(parse_input_json(json.dumps(data)))

    def test_is_sharding_empty_string_falls_back_to_detection(self):
        sharding_sql = "CREATE TABLE `order_0` (`id` int) ENGINE=InnoDB"
        data = {
            "mysql_sql": sharding_sql,
            "day_or_hour": "天表",
            "product_line": "sfst",
            "is_sharding": "",
        }
        result = parse_input_json(json.dumps(data))
        self.assertEqual(result.is_sharding, "是")


class TestParseInputJsonDoubleQuoteRepair(unittest.TestCase):
    """SQL 中含未转义双引号时的自动修复测试。"""

    def test_sql_with_default_empty_double_quotes(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `t` (`name` varchar(64) DEFAULT ""'
            " COMMENT '名称') ENGINE=InnoDB\""
            ', "day_or_hour": "天表", "product_line": "sfst"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        self.assertIn("DEFAULT ''", result.mysql_sql)
        self.assertEqual(result.day_or_hour, "天表")

    def test_sql_with_unescaped_double_quotes(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `t` ('
            '`a` varchar(64) DEFAULT "" COMMENT "名称"'
            ') ENGINE=InnoDB", "day_or_hour": "天表", "product_line": "sfst"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        self.assertIn("DEFAULT ''", result.mysql_sql)
        self.assertIn("COMMENT '名称'", result.mysql_sql)

    def test_sql_with_multiple_double_quoted_columns(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `t` ('
            '`a` varchar DEFAULT "" COMMENT "字段A", '
            '`b` varchar DEFAULT "hello" COMMENT "字段B"'
            ') ENGINE=InnoDB", "day_or_hour": "天表", "product_line": "sfst"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        self.assertIn("DEFAULT ''", result.mysql_sql)
        self.assertIn("DEFAULT 'hello'", result.mysql_sql)
        self.assertIn("COMMENT '字段A'", result.mysql_sql)
        self.assertIn("COMMENT '字段B'", result.mysql_sql)

    def test_properly_escaped_quotes_use_normal_path(self):
        sql = 'CREATE TABLE `t` (`a` varchar DEFAULT "" COMMENT "名称") ENGINE=InnoDB'
        data = {"mysql_sql": sql, "day_or_hour": "天表", "product_line": "sfst"}
        result = parse_input_json(json.dumps(data))
        self.assertIsNotNone(result)
        self.assertIn('DEFAULT ""', result.mysql_sql)
        self.assertIn('COMMENT "名称"', result.mysql_sql)

    def test_repair_with_optional_fields(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `t` (`a` int) COMMENT "表注释"", '
            '"day_or_hour": "天表", "product_line": "sfst", '
            '"dw_layer": "ods", "operate_type": "新建表"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        self.assertIn("COMMENT '表注释'", result.mysql_sql)
        self.assertEqual(result.dw_layer, "ods")
        self.assertEqual(result.operate_type, "新建表")

    def test_multiline_sql_with_double_quotes(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `user_info` (\n'
            '  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT "主键",\n'
            '  `name` varchar(64) DEFAULT "" COMMENT "用户名"\n'
            ') ENGINE=InnoDB COMMENT "用户表"", '
            '"day_or_hour": "天表", "product_line": "sfst"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        self.assertIn("COMMENT '主键'", result.mysql_sql)
        self.assertIn("DEFAULT ''", result.mysql_sql)
        self.assertIn("COMMENT '用户名'", result.mysql_sql)
        self.assertIn("COMMENT '用户表'", result.mysql_sql)
        self.assertIn("\n", result.mysql_sql)

    def test_repair_missing_mysql_sql_key_returns_none(self):
        raw = '{"day_or_hour": "天表", "product_line": "sfst"}'
        result = parse_input_json(raw)
        self.assertIsNone(result)

    def test_repaired_sql_can_parse_table_name(self):
        raw = (
            '{"mysql_sql": "CREATE TABLE `order_detail` ('
            '`id` int COMMENT "主键"'
            ') ENGINE=InnoDB COMMENT "订单明细"", '
            '"day_or_hour": "天表", "product_line": "sfst"}'
        )
        result = parse_input_json(raw)
        self.assertIsNotNone(result)
        table_name = parse_table_name(result.mysql_sql)
        self.assertEqual(table_name, "order_detail")

    def test_irreparable_json_returns_none(self):
        self.assertIsNone(parse_input_json("{totally broken"))
        self.assertIsNone(parse_input_json("not json at all"))


if __name__ == "__main__":
    unittest.main()
