"""项目配置文件"""
from pathlib import Path

# 项目根目录：app/config/settings.py -> 向上3级到项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Excel 输出配置
OUTPUT_BASE_DIR = PROJECT_ROOT.parent / "create-table-output"
EXCEL_FILENAME = "create_table_info.xlsx"

# 日志配置
LOG_DIR = str(PROJECT_ROOT / "logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
