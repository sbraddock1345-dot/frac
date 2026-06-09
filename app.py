import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Frac Pump Data Chart", layout="wide")

st.title("Frac Pump Data Chart")
st.caption("Upload CSV pump data and chart rate, pressure, and slurry data.")

uploaded = st.file_uploader("Upload frac pump CSV", type=["csv"])

REQUIRED_HINTS = {
    "time": ["time", "timestamp", "date", "datetime"],
    "pressure": ["discharge pressure", "treating pressure", "tp", "psi"],
    "rate": ["rate", "slurry rate", "bpm"]
}

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

def make_chart(df, x_col, y_cols, title):
    fig = go.Figure()
    
    # Separate pressure and rate columns
    pressure_cols = [col for col in y_cols if any(pressure in col.lower() for pressure in ["pressure", "psi"])]
    rate_cols = [col for col in y_cols if any(rate in col.lower() for rate in ["rate", "bpm"])]
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
        xaxis_title=x_col,
        yaxis=dict(
            title="Pressure (PSI)",
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

if uploaded is None:
    st.info("Upload a CSV file to begin.")
    st.markdown("""
    **Common columns this app can chart:**
    - Time / Timestamp
    - Treating Pressure PSI
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

    x_col = st.sidebar.selectbox(
        "Time / X-axis column",
        cols,
        index=cols.index(guessed_time) if guessed_time in cols else 0
    )

    default_y = [c for c in [guessed_pressure, "Total Rate" if "Total Rate" in cols else guessed_rate] if c in cols]
    y_cols = st.sidebar.multiselect(
        "Columns to chart",
        cols,
        default=default_y
    )

    if len(rate_columns) > 1:
        st.sidebar.write(f"Combined rate columns: {', '.join(rate_columns)}")
        st.sidebar.write("Using Total Rate when multiple rate columns are present.")

    # Try to convert time column
    x_is_datetime = False
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
    elif pd.api.types.is_numeric_dtype(df[x_col]):
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

    if y_cols:
        st.subheader("Main chart")
        st.write(f"Showing {len(df):,} rows after filtering.")
        st.plotly_chart(make_chart(df, x_col, y_cols, "Frac Pump Data"), use_container_width=True)
    else:
        st.warning("Select at least one column to chart.")

    st.subheader("Raw data preview")
    st.write(f"Loaded {len(df_full):,} rows from the uploaded CSV.")
    preview_options = [50, 100, 200, 500, 1000, "All"]
    preview_limit = st.sidebar.selectbox("Preview rows", preview_options, index=2)
    preview_df = df_full if preview_limit == "All" else df_full.head(preview_limit)
    st.dataframe(preview_df, use_container_width=True)

    st.subheader("Stage / job summary")

    summary_cols = [c for c in y_cols if c in numeric_cols]
    if summary_cols:
        summary = df[summary_cols].agg(["min", "max", "mean"]).T
        summary["range"] = summary["max"] - summary["min"]
        st.dataframe(summary, use_container_width=True)
    else:
        st.info("Select numeric columns to generate summary.")

    st.subheader("Spike / dropout check")

    spike_col = st.selectbox(
        "Column to inspect",
        numeric_cols,
        index=numeric_cols.index(guessed_pressure) if guessed_pressure in numeric_cols else 0
    ) if numeric_cols else None

    if spike_col:
        threshold_pct = st.slider(
            "Flag sudden change greater than percent",
            min_value=5,
            max_value=100,
            value=20,
            step=5
        )

        check = df[[x_col, spike_col]].copy()
        check["change"] = check[spike_col].diff()
        check["change_pct"] = check[spike_col].pct_change().abs() * 100
        flagged = check[check["change_pct"] >= threshold_pct]

        st.write(f"Flagged points in **{spike_col}** with change >= {threshold_pct}%")
        st.dataframe(flagged.head(500), use_container_width=True)

        if not flagged.empty:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df[x_col], y=df[spike_col], mode="lines", name=spike_col))
            fig2.add_trace(go.Scatter(
                x=flagged[x_col],
                y=flagged[spike_col],
                mode="markers",
                name="Flagged",
                marker=dict(size=9)
            ))
            fig2.update_layout(
                title=f"{spike_col} spike/dropout check",
                xaxis_title=x_col,
                yaxis_title=spike_col,
                hovermode="x unified",
                height=500
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Export cleaned data")
    csv_out = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download cleaned CSV",
        csv_out,
        file_name="cleaned_frac_pump_data.csv",
        mime="text/csv"
    )