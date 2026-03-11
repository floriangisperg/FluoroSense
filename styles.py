"""
FluoroSense Dark Lab Theme
Custom styling for fluorescence spectroscopy analysis app
"""

def apply_dark_lab_theme():
    """
    Apply the Dark Lab theme with fluorescence-inspired accents.
    Call this at the top of each page after imports.
    """
    import streamlit as st

    st.markdown("""
    <style>
    /* ========================================
       FLUOROSENSE DARK LAB THEME
       ======================================== */

    /* ---- CSS Variables ---- */
    :root {
        --bg-primary: #0e1117;
        --bg-secondary: #1a1d24;
        --bg-tertiary: #252a33;
        --bg-card: rgba(26, 29, 36, 0.8);
        --bg-glass: rgba(14, 17, 23, 0.7);

        --text-primary: #e4e7eb;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;

        --accent-cyan: #00d4ff;
        --accent-green: #00ff88;
        --accent-violet: #a855f7;
        --accent-amber: #fbbf24;
        --accent-rose: #f472b6;

        --border-color: rgba(255, 255, 255, 0.08);
        --border-glow: rgba(0, 212, 255, 0.3);

        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
        --shadow-glow: 0 0 20px rgba(0, 212, 255, 0.15);

        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 16px;

        --transition-fast: 0.15s ease;
        --transition-normal: 0.3s ease;
        --transition-slow: 0.5s ease;
    }

    /* ---- Global Resets & Base ---- */
    .stApp {
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background:
            radial-gradient(ellipse at 20% 20%, rgba(0, 212, 255, 0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 80%, rgba(168, 85, 247, 0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.02) 0%, transparent 70%);
        pointer-events: none;
        z-index: -1;
    }

    /* ---- Typography ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    h1, h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 2.5rem !important;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent-cyan) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    h2 {
        font-size: 1.75rem !important;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem !important;
    }

    h3 {
        font-size: 1.25rem !important;
        color: var(--accent-cyan) !important;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color);
    }

    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 1rem;
    }

    section[data-testid="stSidebar"] h1 {
        font-size: 1.5rem !important;
        background: none;
        -webkit-text-fill-color: var(--text-primary);
    }

    /* ---- Cards & Containers ---- */
    .stContainer > div {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 1.5rem;
        backdrop-filter: blur(10px);
    }

    /* Glass card effect */
    .glass-card {
        background: var(--bg-glass) !important;
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        padding: 2rem !important;
        box-shadow: var(--shadow-lg), var(--shadow-glow);
    }

    /* ---- Buttons ---- */
    .stButton > button {
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        color: var(--text-primary);
        padding: 0.6rem 1.5rem;
        font-weight: 500;
        transition: all var(--transition-normal);
        box-shadow: var(--shadow-sm);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, rgba(0, 212, 255, 0.1) 100%);
        border-color: var(--accent-cyan);
        box-shadow: var(--shadow-md), 0 0 15px rgba(0, 212, 255, 0.2);
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Primary button variant */
    .stButton > button[kind="primary"],
    .stButton > button.primary {
        background: linear-gradient(135deg, var(--accent-cyan) 0%, #00a8cc 100%);
        border-color: var(--accent-cyan);
        color: var(--bg-primary);
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #00e5ff 0%, var(--accent-cyan) 100%);
        box-shadow: var(--shadow-md), 0 0 25px rgba(0, 212, 255, 0.4);
    }

    /* ---- File Uploader ---- */
    .stFileUploader {
        background: var(--bg-secondary);
        border: 2px dashed var(--border-color);
        border-radius: var(--radius-md);
        padding: 2rem;
        transition: all var(--transition-normal);
    }

    .stFileUploader:hover {
        border-color: var(--accent-cyan);
        background: rgba(0, 212, 255, 0.05);
    }

    .stFileUploader section {
        background: transparent !important;
    }

    /* ---- Tabs ---- */
    .stTabs {
        margin-top: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        padding: 0.25rem;
        border: 1px solid var(--border-color);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: var(--radius-sm);
        padding: 0.75rem 1.5rem;
        color: var(--text-secondary);
        font-weight: 500;
        transition: all var(--transition-fast);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent-cyan) 0%, #00a8cc 100%) !important;
        color: var(--bg-primary) !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* ---- Selectbox & Dropdown ---- */
    .stSelectbox > div > div {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
    }

    .stSelectbox > div > div:hover {
        border-color: var(--accent-cyan);
    }

    /* ---- Dataframe & Tables ---- */
    .stDataFrame {
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        overflow: hidden;
    }

    .stDataFrame table {
        background: var(--bg-secondary) !important;
    }

    .stDataFrame thead th {
        background: var(--bg-tertiary) !important;
        color: var(--accent-cyan) !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }

    .stDataFrame tbody tr:hover {
        background: rgba(0, 212, 255, 0.05) !important;
    }

    /* ---- Metrics ---- */
    [data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 1rem 1.5rem;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    [data-testid="stMetricValue"] {
        color: var(--accent-cyan) !important;
        font-size: 2rem !important;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        color: var(--accent-green) !important;
    }

    [data-testid="stMetricDelta"][aria-label*="negative"],
    [data-testid="stMetricDelta"].negative {
        color: var(--accent-rose) !important;
    }

    /* ---- Expanders ---- */
    .streamlit-expanderHeader {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        padding: 1rem 1.5rem;
        font-weight: 500;
        transition: all var(--transition-fast);
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--accent-cyan);
        background: var(--bg-tertiary);
    }

    .streamlit-expanderContent {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-top: none;
        border-radius: 0 0 var(--radius-md) var(--radius-md);
        padding: 1.5rem;
    }

    /* ---- Checkboxes & Radio ---- */
    .stCheckbox label,
    .stRadio label {
        color: var(--text-primary) !important;
    }

    .stCheckbox input:checked + div,
    .stRadio input:checked + div {
        background: var(--accent-cyan) !important;
        border-color: var(--accent-cyan) !important;
    }

    /* ---- Slider ---- */
    .stSlider [data-baseweb="slider"] {
        background: var(--bg-tertiary);
    }

    .stSlider [data-baseweb="thumb"] {
        background: var(--accent-cyan);
        border: 2px solid var(--accent-cyan);
    }

    /* ---- Progress Bar ---- */
    .stProgress > div > div {
        background: var(--bg-tertiary);
        border-radius: var(--radius-sm);
    }

    .stProgress [data-baseweb="progress-bar"] {
        background: linear-gradient(90deg, var(--accent-cyan), var(--accent-green));
        border-radius: var(--radius-sm);
    }

    /* ---- Info/Warning/Success Boxes ---- */
    .stAlert {
        border-radius: var(--radius-md);
        border: 1px solid;
    }

    .stAlert[data-baseweb="notification"] {
        background: var(--bg-card);
    }

    div[data-testid="stAlert"] > div {
        background: transparent !important;
    }

    /* Info */
    .stAlert:has([data-testid="stIcon"]) {
        border-color: var(--accent-cyan);
    }

    /* Success */
    element.style + .stAlert {
        border-color: var(--accent-green);
    }

    /* Warning */
    .stAlert.warning {
        border-color: var(--accent-amber);
    }

    /* ---- Download Button ---- */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--accent-green) 0%, #00cc6a 100%);
        border-color: var(--accent-green);
        color: var(--bg-primary);
    }

    .stDownloadButton > button:hover {
        box-shadow: var(--shadow-md), 0 0 25px rgba(0, 255, 136, 0.4);
    }

    /* ---- Plotly Charts ---- */
    .js-plotly-plot .plotly .modebar {
        background: var(--bg-tertiary) !important;
        border-radius: var(--radius-sm);
    }

    .js-plotly-plot .plotly .modebar-btn path {
        fill: var(--text-secondary) !important;
    }

    .js-plotly-plot .plotly .modebar-btn:hover path {
        fill: var(--accent-cyan) !important;
    }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-cyan);
    }

    /* ---- Animations ---- */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes pulse-glow {
        0%, 100% {
            box-shadow: 0 0 5px rgba(0, 212, 255, 0.3);
        }
        50% {
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }
    }

    @keyframes shimmer {
        0% {
            background-position: -200% 0;
        }
        100% {
            background-position: 200% 0;
        }
    }

    .animate-fade-in {
        animation: fadeInUp 0.5s ease forwards;
    }

    .animate-pulse-glow {
        animation: pulse-glow 2s ease-in-out infinite;
    }

    /* ---- Utility Classes ---- */
    .text-gradient-cyan {
        background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-green) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .text-gradient-violet {
        background: linear-gradient(135deg, var(--accent-violet) 0%, var(--accent-rose) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .border-glow {
        border: 1px solid var(--accent-cyan);
        box-shadow: var(--shadow-glow);
    }

    /* ---- Header Logo/Title Area ---- */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        margin-bottom: 2rem;
    }

    .main-header h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }

    .main-header .subtitle {
        color: var(--text-secondary);
        font-size: 1.1rem;
    }

    /* ---- Feature Cards for Landing Page ---- */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .feature-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: 2rem;
        transition: all var(--transition-normal);
    }

    .feature-card:hover {
        border-color: var(--accent-cyan);
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg), var(--shadow-glow);
    }

    .feature-card .icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }

    .feature-card h3 {
        color: var(--accent-cyan) !important;
        margin-bottom: 0.75rem !important;
        font-size: 1.25rem !important;
    }

    .feature-card p {
        color: var(--text-secondary);
        line-height: 1.6;
    }

    /* ---- Status Indicators ---- */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.75rem;
        border-radius: var(--radius-sm);
        font-size: 0.875rem;
        font-weight: 500;
    }

    .status-badge.active {
        background: rgba(0, 255, 136, 0.15);
        color: var(--accent-green);
        border: 1px solid var(--accent-green);
    }

    .status-badge.pending {
        background: rgba(251, 191, 36, 0.15);
        color: var(--accent-amber);
        border: 1px solid var(--accent-amber);
    }

    .status-badge.error {
        background: rgba(244, 114, 182, 0.15);
        color: var(--accent-rose);
        border: 1px solid var(--accent-rose);
    }

    /* ---- Hide Streamlit Branding ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ---- Print Styles ---- */
    @media print {
        .stSidebar, #MainMenu, footer, header {
            display: none !important;
        }
        .stApp {
            background: white;
            color: black;
        }
    }
    </style>
    """, unsafe_allow_html=True)


def get_plotly_dark_template():
    """
    Return a Plotly template dict for dark mode charts.
    Use with: fig.update_layout(template=template_dict)
    """
    return {
        'layout': {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(26, 29, 36, 0.5)',
            'font': {
                'color': '#e4e7eb',
                'family': 'Inter, sans-serif'
            },
            'title': {
                'font': {'color': '#e4e7eb', 'size': 18}
            },
            'xaxis': {
                'gridcolor': 'rgba(255,255,255,0.08)',
                'linecolor': 'rgba(255,255,255,0.15)',
                'tickfont': {'color': '#9ca3af'},
                'title': {'font': {'color': '#e4e7eb'}}
            },
            'yaxis': {
                'gridcolor': 'rgba(255,255,255,0.08)',
                'linecolor': 'rgba(255,255,255,0.15)',
                'tickfont': {'color': '#9ca3af'},
                'title': {'font': {'color': '#e4e7eb'}}
            },
            'legend': {
                'font': {'color': '#e4e7eb'},
                'bgcolor': 'rgba(26, 29, 36, 0.8)',
                'bordercolor': 'rgba(255,255,255,0.1)',
                'borderwidth': 1
            },
            'colorway': ['#00d4ff', '#00ff88', '#a855f7', '#fbbf24', '#f472b6', '#06b6d4', '#84cc16', '#f97316']
        }
    }


# Color palette for consistent use throughout the app
COLORS = {
    'cyan': '#00d4ff',
    'green': '#00ff88',
    'violet': '#a855f7',
    'amber': '#fbbf24',
    'rose': '#f472b6',
    'cyan_dark': '#00a8cc',
    'green_dark': '#00cc6a',
}

# Emission-inspired color sequence for multi-trace plots
EMISSION_PALETTE = ['#00d4ff', '#00ff88', '#a855f7', '#fbbf24', '#f472b6', '#06b6d4', '#84cc16', '#f97316']
