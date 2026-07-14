from langchain_core.tools import BaseTool

from tools.chart_generator import generate_chart
from tools.python_executor import execute_python_code
from tools.report_generator import generate_pdf_report, generate_pptx_report
from tools.sql_compiler import compile_and_execute_sql

ALL_TOOLS: list[BaseTool] = [
    execute_python_code,
    compile_and_execute_sql,
    generate_chart,
    generate_pdf_report,
    generate_pptx_report,
]


def get_all_tools() -> list[BaseTool]:
    """Get list of all standard tools registered for agents."""
    return ALL_TOOLS
