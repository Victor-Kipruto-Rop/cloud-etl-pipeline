"""Dashboard generation for ETL pipeline outputs."""

import logging
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def _get_color_from_palette(palette):
    try:
        return sns.color_palette(palette, 1)[0]
    except Exception:
        return sns.color_palette("deep", 1)[0]


def _save_count_plot(df, column, output_path, title, palette="viridis"):
    counts = df[column].value_counts(dropna=False)
    if counts.empty:
        return None

    color = _get_color_from_palette(palette)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=counts.values, y=counts.index, color=color)
    plt.title(title)
    plt.xlabel("Count")
    plt.ylabel(column.replace("_", " ").title())
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved dashboard chart: {output_path}")
    return output_path


def _save_scatter_plot(df, x, y, output_path, title, hue=None, sample=1000):
    if df.empty or x not in df.columns or y not in df.columns:
        return None

    plot_df = df.copy()
    if len(plot_df) > sample:
        plot_df = plot_df.sample(sample, random_state=1)

    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=plot_df, x=x, y=y, hue=hue if hue in plot_df.columns else None, alpha=0.7
    )
    plt.title(title)
    plt.xlabel(x.replace("_", " ").title())
    plt.ylabel(y.replace("_", " ").title())
    if hue and hue in plot_df.columns:
        plt.legend(
            title=hue.replace("_", " ").title(),
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
        )
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved dashboard chart: {output_path}")
    return output_path


def _save_average_price_by_state(df, output_path, title):
    if df.empty or "state" not in df.columns or "sellingprice" not in df.columns:
        return None

    avg_prices = df.groupby("state")["sellingprice"].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 7))
    color = _get_color_from_palette("coolwarm")
    sns.barplot(x=avg_prices.values, y=avg_prices.index, color=color)
    plt.title(title)
    plt.xlabel("Average Selling Price")
    plt.ylabel("State")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved dashboard chart: {output_path}")
    return output_path


def _save_price_distribution_by_condition(df, output_path, title):
    if df.empty or "condition" not in df.columns:
        return None

    plt.figure(figsize=(12, 7))
    sns.histplot(
        df,
        x="sellingprice",
        hue="condition",
        palette="viridis",
        multiple="stack",
        bins=30,
    )
    plt.title(title)
    plt.xlabel("Selling Price")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved dashboard chart: {output_path}")
    return output_path


def _save_top_dealers_by_total_sales(df, output_path, title):
    if df.empty or "seller" not in df.columns or "sellingprice" not in df.columns:
        return None

    dealer_sales = (
        df.groupby("seller")["sellingprice"].sum().sort_values(ascending=False).head(10)
    )
    plt.figure(figsize=(12, 8))
    color = _get_color_from_palette("magma")
    sns.barplot(x=dealer_sales.values, y=dealer_sales.index, color=color)
    plt.title(title)
    plt.xlabel("Total Sales Value")
    plt.ylabel("Seller")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info(f"Saved dashboard chart: {output_path}")
    return output_path


def _build_dashboard_html(output_dir, chart_files, summary):
    html = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "  <title>ETL Dashboard</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 20px; }",
        "    h1, h2 { color: #2c3e50; }",
        "    .summary { margin-bottom: 24px; }",
        "    .chart { margin-bottom: 40px; }",
        "    img { max-width: 100%; height: auto; border: 1px solid #ccc; padding: 8px; background: #fff; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>ETL Dashboard</h1>",
        '  <section class="summary">',
        "    <h2>Summary</h2>",
        "    <ul>",
    ]

    for key, value in summary.items():
        html.append(
            f'      <li><strong>{key.replace("_", " ").title()}:</strong> {value}</li>'
        )

    html.extend(
        [
            "    </ul>",
            "  </section>",
        ]
    )

    for chart in chart_files:
        if chart is None:
            continue
        html.extend(
            [
                '  <section class="chart">',
                f'    <h2>{chart.stem.replace("_", " ").title()}</h2>',
                f'    <img src="{chart.name}" alt="{chart.stem}">',
                "  </section>",
            ]
        )

    html.extend(["</body>", "</html>"])

    dashboard_path = output_dir / "dashboard.html"
    dashboard_path.write_text("\n".join(html), encoding="utf-8")
    logger.info(f"Saved dashboard HTML: {dashboard_path}")
    return dashboard_path


def generate_dashboard(processed_dir: Path, output_dir: Path = Path("visualizations")):
    """Generate dashboard charts and HTML from processed ETL output."""
    processed_dir = Path(processed_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not processed_dir.exists():
        raise FileNotFoundError(f"Processed directory not found: {processed_dir}")

    csv_files = sorted(processed_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No processed CSV files found in: {processed_dir}")

    df = None

    def _normalize_date_value(value):
        if pd.isna(value):
            return pd.NaT
        if isinstance(value, str):
            cleaned = value.strip()
            cleaned = re.sub(r"\s*\(.*\)$", "", cleaned)
            try:
                return pd.to_datetime(
                    cleaned, format="%a %b %d %Y %H:%M:%S GMT%z", errors="raise"
                )
            except (ValueError, OverflowError):
                try:
                    return date_parser.parse(cleaned)
                except (ValueError, OverflowError):
                    return pd.NaT
        return value

    def _read_with_date_parsing(path):
        sample_cols = pd.read_csv(path, nrows=0, low_memory=False).columns.tolist()
        date_cols = [col for col in ["saledate", "sale_date"] if col in sample_cols]
        df_local = pd.read_csv(path, low_memory=False)
        for col in date_cols:
            df_local[col] = df_local[col].apply(_normalize_date_value)
        return df_local

    for csv_file in csv_files:
        if csv_file.name == "car_prices.csv":
            df = _read_with_date_parsing(csv_file)
            break

    if df is None:
        df = _read_with_date_parsing(csv_files[0])

    summary = {
        "processed_rows": int(len(df)),
        "columns": ", ".join(df.columns.tolist()),
        "missing_values": int(df.isna().sum().sum()),
    }

    charts = []
    if "state" in df.columns:
        charts.append(
            _save_count_plot(
                df, "state", output_dir / "state_distribution.png", "State Distribution"
            )
        )
    if "condition" in df.columns:
        charts.append(
            _save_count_plot(
                df,
                "condition",
                output_dir / "condition_distribution.png",
                "Condition Distribution",
                palette="coolwarm",
            )
        )
    if "mmr" in df.columns and "sellingprice" in df.columns:
        charts.append(
            _save_scatter_plot(
                df,
                "mmr",
                "sellingprice",
                output_dir / "selling_price_vs_mmr.png",
                "Selling Price vs MMR",
                hue="condition",
            )
        )
    if "seller" in df.columns:
        seller_counts = df["seller"].value_counts().head(10)
        seller_plot = output_dir / "top_sellers.png"
        plt.figure(figsize=(10, 6))
        color = _get_color_from_palette("magma")
        sns.barplot(x=seller_counts.values, y=seller_counts.index, color=color)
        plt.title("Top 10 Sellers by Processed Records")
        plt.xlabel("Count")
        plt.ylabel("Seller")
        plt.tight_layout()
        plt.savefig(seller_plot)
        plt.close()
        logger.info(f"Saved dashboard chart: {seller_plot}")
        charts.append(seller_plot)

        total_sales_plot = output_dir / "top_10_dealers_by_sales.png"
        total_sales_chart = _save_top_dealers_by_total_sales(
            df, total_sales_plot, "Top 10 Dealers by Total Sales"
        )
        if total_sales_chart is not None:
            charts.append(total_sales_chart)

    charts.append(
        _save_average_price_by_state(
            df, output_dir / "car_prices_by_state.png", "Average Selling Price by State"
        )
    )
    charts.append(
        _save_price_distribution_by_condition(
            df,
            output_dir / "sales_condition_distribution.png",
            "Selling Price Distribution by Condition",
        )
    )

    dashboard_path = _build_dashboard_html(output_dir, charts, summary)
    return {
        "dashboard_path": dashboard_path,
        "charts": [c for c in charts if c is not None],
        "summary": summary,
    }
