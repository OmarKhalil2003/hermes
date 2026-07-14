import base64
import io
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from langchain_core.tools import tool


@tool
def generate_chart(
    chart_type: str,
    data: list[dict[str, Any]],
    title: str,
    x_label: str,
    y_label: str,
    x_key: str,
    y_key: str,
) -> str:
    """Generate a Matplotlib chart and return it as a base64 encoded PNG image string.

    Args:
        chart_type: The type of chart to generate ('bar', 'line', 'scatter', 'pie').
        data: A list of data dictionaries.
        title: Chart title.
        x_label: Label for the X-axis (or category label).
        y_label: Label for the Y-axis (or value label).
        x_key: Dictionary key to extract X-axis values from.
        y_key: Dictionary key to extract Y-axis values from.

    Returns:
        A base64 encoded string representing the PNG image, or an error message.
    """
    try:
        if not data:
            return "Error: No data provided to generate chart."

        from typing import cast

        x_values = [str(row.get(x_key)) for row in data]
        y_values = [row.get(y_key) for row in data]

        # Convert values to numeric
        y_numeric: list[float] = []
        for val in y_values:
            try:
                y_numeric.append(float(val) if val is not None else 0.0)
            except (ValueError, TypeError):
                y_numeric.append(0.0)

        fig, ax = plt.subplots(figsize=(8, 5))

        chart_type_lower = chart_type.lower().strip()
        if chart_type_lower == "bar":
            ax.bar(x_values, y_numeric, color="royalblue", edgecolor="navy")
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            plt.xticks(rotation=45, ha="right")
        elif chart_type_lower == "line":
            ax.plot(
                x_values,
                y_numeric,
                color="forestgreen",
                marker="o",
                linestyle="-",
                linewidth=2,
            )
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            plt.xticks(rotation=45, ha="right")
        elif chart_type_lower == "scatter":
            ax.scatter(
                x_values,
                y_numeric,
                color="darkorange",
                edgecolors="red",
                s=50,
            )
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            plt.xticks(rotation=45, ha="right")
        elif chart_type_lower == "pie":
            ax.pie(
                y_numeric,
                labels=x_values,
                autopct="%1.1f%%",
                colors=cast(Any, plt.cm.tab20).colors,
            )
        else:
            plt.close(fig)
            return (
                f"Error: Unsupported chart type: {chart_type}. "
                "Must be 'bar', 'line', 'scatter', or 'pie'."
            )

        ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)

        base64_str = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{base64_str}"

    except Exception as e:
        return f"Error generating chart: {e!s}"
