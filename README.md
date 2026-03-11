# FluoroSense
[This app](https://tuwien-jasco.streamlit.app/) has been created for scientific research in the area of protein kinetics using a Jasco spectro-fluorimeter. It offers extended analytics with respect to the commercial software and fast data analysis of protein analysis.

## Running with uv

Install dependencies and run the app using uv:

```powershell
# Install dependencies from pyproject.toml
uv sync

# Run the Streamlit app
uv run streamlit run Main_Page.py
```

Optional: export a `requirements.txt`-style lock for reproducibility:

```powershell
uv export --format requirements-txt -o requirements.lock.txt
```

