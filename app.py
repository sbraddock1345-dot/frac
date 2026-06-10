from datetime import datetime
from io import BytesIO
from pathlib import Path
import re

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Frac Pump Data Chart", layout="wide")

LOGO_PATH = "assets/max-fluid-power-logo.png"

header_left, header_right = st.columns([0.78, 0.22])
with header_left:
    st.title("Frac Pump Data Chart")
    st.caption("Upload CSV pump data and chart rate, pressure, and slurry data.")
with header_right:
    st.image(LOGO_PATH, use_container_width=True)

uploaded = st.file_uploader("Upload frac pump CSV", type=["csv"])

REQUIRED_HINTS = {
    "date": ["date"],
    "time": ["time"],
    "pressure": ["discharge psi", "discharge pressure", "pressure", "treating pressure", "tp", "psi"],
    "rate": ["rate", "slurry rate", "bpm"]
}


def clean_filename(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "stage_report"


def guess_column(columns, keywords):
    lower_map = {c.lower().strip(): c for c in columns}
    for key in keywords:
        for lc, orig in lower_map.items():
            if key in lc:
                return orig
    return None


def find_columns(columns, keywords):
    lower_map = {c.lower().strip(): c for c in columns}
    matched = []
    for lc, orig in lower_map.items():
        if any(key in lc for key in keywords):
            matched.append(orig)
    return matched


def read_csv(file):
    df = pd.read_csv(file, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def is_rate_column(column):
    return any(token in column.lower() for token in ["rate", "bpm"])


def format_report_time(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return parsed.strftime("%b %d, %Y %I:%M:%S %p")
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def format_stage_label(stage_name):
    stage_name = stage_name.strip()
    if not stage_name:
        return ""
    if stage_name.lower().startswith("stage"):
        return stage_name
    return f"Stage {stage_name}"


def chart_x_axis(x_col):
    if x_col == "_datetime":
        return {"title": "Time", "tickformat": "%H:%M:%S"}
    return {"title": x_col}


def make_chart(df, x_col, y_cols, title):
    fig = go.Figure()

    # Separate pressure and rate columns
    pressure_cols = [col for col in y_cols if any(p in col.lower() for p in ["discharge", "pressure", "psi"])]
    rate_cols = [col for col in y_cols if any(r in col.lower() for r in ["rate", "bpm"])]
    other_cols = [col for col in y_cols if col not in pressure_cols and col not in rate_cols]

    # Add pressure traces on primary y-axis
    for col in pressure_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode="lines",
            name=col,
            yaxis="y1"
        ))

    # Add rate traces on secondary y-axis
    for col in rate_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode="lines",
            name=col,
            yaxis="y2"
        ))

    # Add other traces on primary y-axis
    for col in other_cols:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode="lines",
            name=col,
            yaxis="y1"
        ))

    fig.update_layout(
        title=title,
        xaxis=chart_x_axis(x_col),
        yaxis=dict(
            title="Discharge PSI",
            side="left"
        ),
        yaxis2=dict(
            title="Rate (BPM)",
            overlaying="y",
            side="right"
        ),
        hovermode="x unified",
        height=600
    )
    return fig


def make_report_chart_image(df, x_col, y_cols):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax_pressure = plt.subplots(figsize=(10.5, 5.2), dpi=160)
    ax_rate = ax_pressure.twinx()

    pressure_cols = [col for col in y_cols if any(p in col.lower() for p in ["discharge", "pressure", "psi"])]
    rate_cols = [col for col in y_cols if is_rate_column(col)]
    other_cols = [col for col in y_cols if col not in pressure_cols and col not in rate_cols]

    for col in pressure_cols + other_cols:
        ax_pressure.plot(df[x_col], df[col], linewidth=1.0, label=col)

    for col in rate_cols:
        ax_rate.plot(df[x_col], df[col], linewidth=1.0, linestyle="--", label=col)

    ax_pressure.set_xlabel("Time" if x_col == "_datetime" else x_col)
    if x_col == "_datetime":
        ax_pressure.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    ax_pressure.set_ylabel("Discharge PSI")
    ax_rate.set_ylabel("Rate (BPM)")
    ax_pressure.grid(True, alpha=0.25)

    handles_left, labels_left = ax_pressure.get_legend_handles_labels()
    handles_right, labels_right = ax_rate.get_legend_handles_labels()
    fig.legend(
        handles_left + handles_right,
        labels_left + labels_right,
        loc="lower center",
        ncol=3,
        fontsize=7,
        frameon=False,
    )
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    image_buffer.seek(0)
    return image_buffer


def dataframe_to_table_rows(df, max_rows=None):
    if df is None or df.empty:
        return []

    table_df = df.copy()
    if max_rows:
        table_df = table_df.head(max_rows)
    rows = [list(table_df.columns)]
    for _, row in table_df.iterrows():
        formatted = []
        for value in row:
            if pd.isna(value):
                formatted.append("")
            elif isinstance(value, float):
                formatted.append(f"{value:,.2f}")
            else:
                formatted.append(str(value))
        rows.append(formatted)
    return rows


def make_pumpdown_summary_table(summary):
    summary_table = summary.copy()
    labels = []
    sort_order = []

    for column in summary_table.index:
        column_lower = str(column).lower()
        if any(token in column_lower for token in ["discharge", "pressure", "psi"]):
            labels.append("Pressure")
            sort_order.append(0)
        elif is_rate_column(str(column)):
            labels.append("Rate")
            sort_order.append(1)
        else:
            labels.append(str(column))
            sort_order.append(2)

    summary_table.insert(0, "Measurement", labels)
    summary_table["_sort_order"] = sort_order
    summary_table = summary_table.sort_values("_sort_order").drop(columns="_sort_order")
    return summary_table


def make_stage_report_pdf(
    df,
    x_col,
    y_cols,
    well_name,
    stage_name,
    selected_range,
    summary,
    bbls_df,
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    title_parts = [part for part in [well_name.strip(), format_stage_label(stage_name)] if part]
    report_title = " - ".join(title_parts) if title_parts else "Frac Pump Stage Report"
    header_text = [
        Paragraph(report_title, styles["Title"]),
        Paragraph(f"Created: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
        Paragraph(f"Time: {selected_range}", styles["Normal"]),
    ]
    logo_path = Path(LOGO_PATH)
    if logo_path.exists():
        logo = Image(str(logo_path), width=1.2 * inch, height=0.99 * inch)
        header = Table([[header_text, logo]], colWidths=[5.55 * inch, 1.55 * inch])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header)
    else:
        story.extend(header_text)
    story.append(Spacer(1, 0.16 * inch))

    if y_cols and not df.empty:
        chart_image = make_report_chart_image(df, x_col, y_cols)
        story.append(Image(chart_image, width=7.2 * inch, height=3.55 * inch))
        story.append(Spacer(1, 0.18 * inch))

    if summary is not None and not summary.empty:
        story.append(Paragraph("Pumpdown Summary", styles["Heading2"]))
        summary_rows = dataframe_to_table_rows(make_pumpdown_summary_table(summary))
        summary_table = Table(summary_rows, repeatRows=1)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.18 * inch))

    if bbls_df is not None and not bbls_df.empty:
        story.append(Paragraph("Total Barrels Pumped", styles["Heading2"]))
        pdf_bbls_df = bbls_df.drop(columns=["Column"], errors="ignore")
        bbls_rows = dataframe_to_table_rows(pdf_bbls_df)
        bbls_table = Table(bbls_rows, repeatRows=1)
        bbls_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(bbls_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if uploaded is None:
    st.info("Upload a CSV file to begin.")
    st.markdown("""
    **Common columns this app can chart:**
    - Time / Timestamp
    - Discharge PSI
    - Slurry Rate BPM
    """)
else:
    df = read_csv(uploaded)
    df_full = df.copy()

    cols = list(df.columns)

    guessed_time = guess_column(cols, REQUIRED_HINTS["time"])
    guessed_pressure = guess_column(cols, REQUIRED_HINTS["pressure"])
    guessed_rate = guess_column(cols, REQUIRED_HINTS["rate"])

    rate_columns = find_columns(cols, REQUIRED_HINTS["rate"])
    if len(rate_columns) > 1:
        df["Total Rate"] = df[rate_columns].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        if "Total Rate" not in cols:
            cols.append("Total Rate")

    st.sidebar.header("Column setup")

    use_separate_date_time = st.sidebar.checkbox("Use separate date and time columns", value=True)

    if use_separate_date_time:
        guessed_date = guess_column(cols, REQUIRED_HINTS["date"])
        date_col = st.sidebar.selectbox(
            "Date column",
            cols,
            index=cols.index(guessed_date) if guessed_date in cols else 0
        )
        time_col = st.sidebar.selectbox(
            "Time column",
            cols,
            index=cols.index(guessed_time) if guessed_time in cols else 0
        )
        x_col = None
    else:
        x_col = st.sidebar.selectbox(
            "Time / X-axis column",
            cols,
            index=cols.index(guessed_time) if guessed_time in cols else 0
        )
        date_col = None
        time_col = None

    default_y = [c for c in [guessed_pressure, "Total Rate" if "Total Rate" in cols else guessed_rate] if c in cols]
    y_cols = st.sidebar.multiselect(
        "Columns to chart",
        cols,
        default=default_y
    )

    if len(rate_columns) > 1:
        st.sidebar.write(f"Combined rate columns: {', '.join(rate_columns)}")
        st.sidebar.write("Using Total Rate when multiple rate columns are present.")

    # Handle datetime conversion
    x_is_datetime = False
    if use_separate_date_time and date_col and time_col:
        try:
            df["_datetime"] = pd.to_datetime(df[date_col].astype(str) + " " + df[time_col].astype(str))
            x_col = "_datetime"
            x_is_datetime = True
        except Exception as e:
            st.sidebar.error(f"Could not combine date and time columns: {e}")
            x_col = None
    elif x_col:
        try:
            df[x_col] = pd.to_datetime(df[x_col])
            x_is_datetime = True
        except Exception:
            pass

    numeric_cols = []
    for c in cols:
        if c != x_col:
            converted = pd.to_numeric(df[c], errors="coerce")
            if converted.notna().sum() > 0:
                df[c] = converted
                numeric_cols.append(c)

    selected_range = "All rows"

    if x_is_datetime:
        st.sidebar.subheader("Time range")
        min_time = df[x_col].min()
        max_time = df[x_col].max()
        if min_time == max_time:
            time_range = (min_time, max_time)
            st.sidebar.write("Only one timestamp is available.")
        else:
            min_time_dt = min_time.to_pydatetime()
            max_time_dt = max_time.to_pydatetime()
            time_range = st.sidebar.slider(
                "Select time range",
                min_value=min_time_dt,
                max_value=max_time_dt,
                value=(min_time_dt, max_time_dt),
                format="YYYY-MM-DD HH:mm"
            )
        df = df[(df[x_col] >= time_range[0]) & (df[x_col] <= time_range[1])]
        selected_range = f"{format_report_time(time_range[0])} to {format_report_time(time_range[1])}"
    elif x_col and pd.api.types.is_numeric_dtype(df[x_col]):
        st.sidebar.subheader("X-axis range")
        min_x = float(df[x_col].min())
        max_x = float(df[x_col].max())
        if min_x != max_x:
            x_range = st.sidebar.slider(
                "Select X range",
                min_value=min_x,
                max_value=max_x,
                value=(min_x, max_x)
            )
            df = df[(df[x_col] >= x_range[0]) & (df[x_col] <= x_range[1])]
            selected_range = f"{format_report_time(x_range[0])} to {format_report_time(x_range[1])}"

    st.sidebar.subheader("Report setup")
    well_name = st.sidebar.text_input("Well name", placeholder="Example: Smith 12H")
    stage_name = st.sidebar.text_input("Stage", placeholder="Example: Stage 7")
    report_download_container = st.sidebar.container()

    if y_cols:
        st.subheader("Main chart")
        st.write(f"Showing {len(df):,} rows after filtering.")
        chart_title_parts = [part for part in [well_name.strip(), format_stage_label(stage_name)] if part]
        chart_title = " - ".join(chart_title_parts) if chart_title_parts else "Frac Pump Data"
        main_chart_fig = make_chart(df, x_col, y_cols, chart_title)
        st.plotly_chart(main_chart_fig, use_container_width=True)
    else:
        main_chart_fig = None
        st.warning("Select at least one column to chart.")

    show_data_tools = st.sidebar.checkbox("Show raw data & export", value=True)

    st.subheader("Stage / job summary")

    summary_cols = [c for c in y_cols if c in numeric_cols]
    summary = None
    bbls_df = None
    if summary_cols:
        # Filter to only rows where any rate column is > 0.1
        rate_cols_for_filter = [c for c in summary_cols if is_rate_column(c)]
        if rate_cols_for_filter:
            df_filtered = df[df[rate_cols_for_filter].max(axis=1) > 0.1]
        else:
            df_filtered = df

        summary = df_filtered[summary_cols].agg(["min", "max", "mean"]).T
        summary.columns = ["Min", "Max", "Average"]

        # Add total bbls pumped for rate columns
        rate_cols_in_summary = [c for c in summary_cols if is_rate_column(c)]
        if rate_cols_in_summary:
            st.dataframe(summary, use_container_width=True)
            st.subheader("Total Barrels Pumped")
            total_bbls = {}
            for col in rate_cols_in_summary:
                # Each row is 1 second, rate is in BPM (barrels per minute)
                # Convert to barrels per second: rate_bpm / 60
                total_bbls[col] = (df[col].sum() / 60)
            if total_bbls:
                bbls_df = pd.DataFrame(list(total_bbls.items()), columns=["Column", "Total Barrels"])
                st.dataframe(bbls_df, use_container_width=True)
        else:
            st.dataframe(summary, use_container_width=True)
    else:
        st.info("Select numeric columns to generate summary.")

    if show_data_tools:
        st.subheader("Raw data preview")
        st.write(f"Loaded {len(df_full):,} rows from the uploaded CSV.")
        preview_options = [50, 100, 200, 500, 1000, "All"]
        preview_limit = st.sidebar.selectbox("Preview rows", preview_options, index=2)
        preview_df = df_full if preview_limit == "All" else df_full.head(preview_limit)
        st.dataframe(preview_df, use_container_width=True)

        st.subheader("Export cleaned data")
        csv_out = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download cleaned CSV",
            csv_out,
            file_name="cleaned_frac_pump_data.csv",
            mime="text/csv"
        )

    with report_download_container:
        if not y_cols:
            st.info("Select chart columns before creating a PDF report.")
        elif not x_col:
            st.info("Select or create a valid time/X-axis column before creating a PDF report.")
        elif df.empty:
            st.info("No rows are available in the selected range for a PDF report.")
        else:
            report_label_parts = [part for part in [well_name, stage_name] if part.strip()]
            report_file_base = clean_filename("_".join(report_label_parts)) if report_label_parts else "frac_pump_stage_report"
            try:
                pdf_bytes = make_stage_report_pdf(
                    df=df,
                    x_col=x_col,
                    y_cols=y_cols,
                    well_name=well_name,
                    stage_name=stage_name,
                    selected_range=selected_range,
                    summary=summary,
                    bbls_df=bbls_df,
                )
                st.download_button(
                    "Download PDF report",
                    pdf_bytes,
                    file_name=f"{report_file_base}.pdf",
                    mime="application/pdf",
                )
            except ImportError:
                st.error("PDF report dependencies are missing. Install requirements.txt and restart the app.")
            except Exception as e:
                st.error(f"Could not create PDF report: {e}")
