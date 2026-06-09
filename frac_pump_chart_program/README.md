# Frac Pump Data Chart Program

This is a simple Streamlit app for charting frac pump CSV data.

## What it does
- Upload CSV data
- Auto-detects common frac columns
- Charts pressure, rate, sand concentration, and proppant totals
- Shows min/max/average summary
- Flags sudden spikes or dropouts
- Exports cleaned CSV

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
# Run the app directly with Streamlit from the package directory
streamlit run app.py
```

```bash
# Or run via the package entry point
python -m frac_pump_chart_program
```

```bash
# Install the package locally and use the console script
python -m pip install -e .
frac-pump-chart
```

## Best CSV columns
The app works best with columns like:

- Time
- Treating Pressure PSI
- Slurry Rate BPM