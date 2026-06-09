from pathlib import Path
import sys

try:
    import streamlit.web.cli as stcli
except ImportError:
    import streamlit.cli as stcli


def main() -> int:
    script_path = Path(__file__).with_name("app.py")
    if not script_path.exists():
        raise FileNotFoundError(f"Unable to find Streamlit app: {script_path}")

    sys.argv = ["streamlit", "run", str(script_path)]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())
