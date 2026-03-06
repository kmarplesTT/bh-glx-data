"""Excel reporting module for generating test summaries.

This module provides functionality to:
- Generate Excel summary reports from CSV test data
- Manage Excel templates
- Update pivot tables
"""

from bh_glx_data.excel_reporting.generator import (
    compile_test_data,
    generate_excel_summary,
    group_csvs_by_system,
)
from bh_glx_data.excel_reporting.templates import (
    load_template,
    paste_data_to_sheet,
    refresh_pivot_tables,
    update_pivot_table_source,
)

__all__ = [
    "generate_excel_summary",
    "compile_test_data",
    "group_csvs_by_system",
    "load_template",
    "paste_data_to_sheet",
    "update_pivot_table_source",
    "refresh_pivot_tables",
]
