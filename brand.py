# brand.py — VERKVIST Brand Identity
# Shared across all VERKVIST apps (RIAQ PWA, ATMO, etc.)
# Update here, applies everywhere.

COLOURS = {
    # Primary brand colours (from logo)
    "dark_green":    "#20343b",   # Logo dark element — primary brand colour
    "mid_green":     "#598d80",   # Logo mid element — secondary brand colour
    "light_green":   "#a4b5bc",   # Logo light element / muted accents

    # UI colours
    "background":    "#ffffff",   # Page background
    "surface":       "#f5f7f7",   # Card / sidebar background
    "border":        "#e0e8e6",   # Dividers and borders
    "text_primary":  "#1a1a1a",   # Main body text
    "text_secondary":"#4a5568",   # Muted / secondary text
    "text_heading":  "#20343b",   # Headings — same as dark green

    # Status colours (keep neutral — not part of VERKVIST brand)
    "success":       "#2d7a4f",
    "warning":       "#b7791f",
    "error":         "#c53030",
}

FONTS = {
    "heading":  "sans-serif",     # All caps for major headings
    "body":     "sans-serif",     # Clean sans-serif body
    "size_h1":  "2rem",
    "size_h2":  "1.5rem",
    "size_h3":  "1.1rem",
    "size_body":"1rem",
    "size_sm":  "0.875rem",
}

# Streamlit custom CSS — inject via st.markdown()
STREAMLIT_CSS = f"""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {COLOURS["dark_green"]};
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}

    /* Main headings */
    h1, h2, h3 {{
        color: {COLOURS["dark_green"]} !important;
        font-family: {FONTS["heading"]};
    }}

    /* Primary button */
    .stButton > button {{
        background-color: {COLOURS["mid_green"]};
        color: white;
        border: none;
        border-radius: 4px;
    }}
    .stButton > button:hover {{
        background-color: {COLOURS["dark_green"]};
        color: white;
    }}

    /* Metric cards */
    [data-testid="metric-container"] {{
        background-color: {COLOURS["surface"]};
        border-left: 4px solid {COLOURS["mid_green"]};
        padding: 1rem;
        border-radius: 4px;
    }}

    /* Footer */
    .verkvist-footer {{
        background-color: {COLOURS["dark_green"]};
        color: white;
        text-align: center;
        padding: 0.5rem;
        font-size: {FONTS["size_sm"]};
        margin-top: 2rem;
    }}
</style>
"""

# Chart colour palette — distinct from UI brand colours for readability
# Use these for all Plotly/matplotlib charts across all apps
CHART_COLOURS = [
    "#598d80",   # Mid green — primary series (anchors VERKVIST brand)
    "#2e7fa3",   # Teal blue — secondary series
    "#d4854a",   # Warm amber — tertiary series
    "#7c6fa0",   # Slate purple — quaternary series
    "#c85f5f",   # Coral — fifth series
    "#4a9e6b",   # Fresh green — sixth series
]

CHART_SPECIAL = {
    "rejected":        "#a0aab4",   # Grey — rejected/filtered data points
    "purge_threshold": "#e07b30",   # Orange — purge detection threshold line
    "mean_line":       "#20343b",   # Dark green — mean/median reference lines
    "r_squared_low":   "#c85f5f",   # Coral — low R² quality
    "r_squared_high":  "#598d80",   # Mid green — high R² quality
}

# App identity per product
APPS = {
    "riaq_pwa": {
        "name_en": "RIAQ PWA",
        "name_is": "RIAQ PWA",
        "tagline_en": "Ventilation Rate Analysis",
        "tagline_is": "Greiningar á loftskiptum",
    },
    "atmo": {
        "name_en": "ATMO",
        "name_is": "ATMO",
        "tagline_en": "Indoor Air Quality Reporting",
        "tagline_is": "Skýrslur um loftgæði innanhúss",
    },
}
