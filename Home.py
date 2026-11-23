"""
FluoroSense - Fluorescence Spectroscopy Analysis
Main landing page with Dark Lab theme
"""
import streamlit as st

# Page config must be first
st.set_page_config(
    layout="wide",
    page_title="FluoroSense",
    page_icon="🔬",
    initial_sidebar_state="expanded"
)

# Import and apply theme
from styles import apply_dark_lab_theme
apply_dark_lab_theme()

from pathlib import Path

# Footer credit URLs (same institutions as the LysoSense app)
CDLAB_URL = "https://www.tuwien.at/en/cdl/ibp4"
CDG_URL = "https://www.cdg.ac.at/en/research-units/labor/inclusion-body-processing-40"
BI_URL = "https://www.boehringer-ingelheim.com/"
IBD_URL = "https://www.tuwien.at/en/tch/icebe/ibdgroup"
TUWIEN_URL = "https://www.tuwien.at/en/"


def _render_credit_logos() -> None:
    """Clickable logo strip shown in the page footer.

    Every logo — including the Boehringer Ingelheim SVG — is embedded as a
    base64 data-URI ``<img>`` tag. LysoSense inlines the SVG markup because a
    data-URI ``<img>`` can be blocked by the component iframe's CSP; ``st.html``
    injects into the main page DOM (no iframe), so that workaround is
    unnecessary here. Inlining the raw ``<svg>`` also collapses to zero width
    as a flex item (viewBox-only SVGs have no intrinsic size), which is why it
    rendered with no space at all.
    """
    import base64

    base = Path(__file__).parent / "assets"
    items = [
        ("ibd_logo.png", IBD_URL),
        ("tuwien_logo.webp", TUWIEN_URL),
        ("bi_logo.svg", BI_URL),
        ("cdg_logo.png", CDG_URL),
    ]
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    parts: list[str] = []
    for name, url in items:
        path = base / name
        if not path.exists():
            continue
        uri = "data:" + mime.get(path.suffix.lower(), "image/png") + ";base64,"
        uri += base64.b64encode(path.read_bytes()).decode()
        parts.append(
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'style="display:inline-flex;align-items:center;height:54px;margin:0 16px;">'
            f'<img src="{uri}" style="max-height:54px;max-width:180px;width:auto;"></a>'
        )
    if parts:
        st.html(
            '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;">'
            + "".join(parts)
            + "</div>"
        )

# Hero Section
st.markdown("""
<div style="text-align: center; padding: 3rem 1rem 2rem;">
    <h1 style="font-size: 4rem; font-weight: 700; background: linear-gradient(135deg, #00d4ff 0%, #00ff88 50%, #a855f7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">FluoroSense</h1>
    <p style="font-size: 1.4rem; color: #9ca3af; font-weight: 300; margin-bottom: 1.5rem;">Fluorescence Spectroscopy Analysis Platform</p>
    <span style="display: inline-block; background: rgba(0, 212, 255, 0.1); border: 1px solid rgba(0, 212, 255, 0.3); border-radius: 20px; padding: 0.5rem 1.25rem; color: #00d4ff; font-size: 0.9rem; font-weight: 500;">Jasco Spectrofluorometer Data Processing</span>
</div>
""", unsafe_allow_html=True)

# Navigation buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔬 Individual Spectra", width='stretch'):
            st.switch_page("pages/1_🔬_Individual_Spectra.py")
    with c2:
        if st.button("⏳ Time Series Analysis", width='stretch'):
            st.switch_page("pages/2_⏳_Time_Series_Measurement.py")

st.markdown("---")

# Feature Cards
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div style="background: rgba(26, 29, 36, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 2rem;">
        <span style="font-size: 2.5rem;">⏳</span>
        <h3 style="color: #00d4ff; margin: 1rem 0 0.75rem;">Time Series Measurement</h3>
        <p style="color: #9ca3af; line-height: 1.7;">Analyze protein refolding kinetics through time-resolved fluorescence measurements.</p>
        <ul style="color: #9ca3af; margin-left: 1rem;">
            <li>Batch processing of multiple conditions</li>
            <li>Average Emission Wavelength (AEW) tracking</li>
            <li>Kinetic fitting with exponential models</li>
            <li>Spectral phase portraits</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: rgba(26, 29, 36, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 2rem;">
        <span style="font-size: 2.5rem;">🔬</span>
        <h3 style="color: #00d4ff; margin: 1rem 0 0.75rem;">Individual Spectra</h3>
        <p style="color: #9ca3af; line-height: 1.7;">Process and visualize single fluorescence emission spectra.</p>
        <ul style="color: #9ca3af; margin-left: 1rem;">
            <li>Interactive spectrum visualization</li>
            <li>Blank subtraction & baseline correction</li>
            <li>Peak detection & analysis</li>
            <li>Multiple export formats</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Science Section
st.header("Measurement Principles")

st.markdown("""
<div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem;">
    <div style="font-size: 2rem;">🧬</div>
    <div>
        <h4 style="color: #00d4ff; margin-bottom: 0.5rem;">Intrinsic Fluorescence</h4>
        <p style="color: #9ca3af; line-height: 1.7;">Fluorescence emission spectra originate from <strong>tryptophan</strong> and <strong>tyrosine</strong> residues in the protein sequence. These aromatic amino acids are sensitive to the hydrophobicity of their local environment.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem;">
    <div style="font-size: 2rem;">🔄</div>
    <div>
        <h4 style="color: #00d4ff; margin-bottom: 0.5rem;">Folding Monitoring</h4>
        <p style="color: #9ca3af; line-height: 1.7;">In the <strong>native state</strong>, hydrophobic residues are buried in the protein core. In the <strong>denatured state</strong>, they become exposed to solvent. This causes a <em>red-shift</em> in fluorescence emission as the protein unfolds.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display: flex; align-items: flex-start; gap: 1.5rem; margin-bottom: 1.5rem;">
    <div style="font-size: 2rem;">📊</div>
    <div>
        <h4 style="color: #00d4ff; margin-bottom: 0.5rem;">Average Emission Wavelength (AEW)</h4>
        <p style="color: #9ca3af; line-height: 1.7;">The AEW provides a robust, intensity-independent metric for tracking spectral shifts. As refolding proceeds, the AEW decreases (blue-shift) indicating burial of aromatic residues.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# AEW Formula
st.markdown("""
<div style="background: rgba(0, 212, 255, 0.05); border: 1px solid rgba(0, 212, 255, 0.2); border-radius: 12px; padding: 1.5rem; text-align: center; margin: 1.5rem 0;">
    <p style="color: #00d4ff; margin-bottom: 0.5rem; font-weight: 600;">AEW Calculation</p>
</div>
""", unsafe_allow_html=True)

st.latex(r'\text{AEW} = \frac{\sum_{i}^{j} \text{Intensity}_i \times \text{Wavelength}_i}{\sum_{i}^{j} \text{Intensity}_i}')

st.markdown("---")

# Footer: logo strip + funding disclaimer
st.markdown("""
<div style="text-align: center; margin-top: 2rem;">
    <p style="color: #6b7280; font-size: 0.85rem;">FluoroSense — Fluorescence Spectroscopy Analysis Platform</p>
</div>
""", unsafe_allow_html=True)

_render_credit_logos()
st.caption(
    "A tool of the CD Laboratory for [Inclusion Body Processing 4.0](%s), "
    "developed in the [IBD Group — Integrated Bioprocess Development](%s) "
    "at [TU Wien](%s). Funded by the "
    "[Christian Doppler Gesellschaft](%s) and [Boehringer Ingelheim](%s)."
    % (CDLAB_URL, IBD_URL, TUWIEN_URL, CDG_URL, BI_URL)
)
