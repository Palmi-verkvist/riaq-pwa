import streamlit as st

from analysis.decay_engine import QCParams, run_analysis
from components.upload import render_upload_page
from components.dashboard import render_dashboard
from components.export import render_export_page
from translations import t

st.set_page_config(
    page_title="RIAQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "lang": "en",
    "df": None,
    "results": None,
    "rejected": None,
    "page": "upload",
    "selected_houses": None,
    "date_start": None,
    "date_end": None,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

lang = st.session_state.lang

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("RIAQ")

    # Language toggle
    lang_choice = st.radio(
        t("language", lang),
        options=["EN", "IS"],
        index=0 if lang == "en" else 1,
        horizontal=True,
        label_visibility="collapsed",
    )
    new_lang = "en" if lang_choice == "EN" else "is"
    if new_lang != lang:
        st.session_state.lang = new_lang
        st.rerun()

    st.divider()

    # Navigation
    _pages = [
        ("upload",    t("page_upload", lang)),
        ("dashboard", t("page_dashboard", lang)),
        ("export",    t("page_export", lang)),
    ]
    _page_map = dict(_pages)

    page = st.radio(
        "",
        options=[p[0] for p in _pages],
        format_func=lambda k: _page_map[k],
        index=[p[0] for p in _pages].index(st.session_state.page),
        label_visibility="collapsed",
    )
    st.session_state.page = page

    st.divider()

    # Analysis settings
    st.subheader(t("sidebar_title", lang))

    ambient = st.number_input(
        t("ambient_co2", lang),
        min_value=350, max_value=600, value=420, step=10,
    )

    with st.expander(t("advanced_qc", lang), expanded=False):
        min_final_co2 = st.number_input(
            t("min_final_co2", lang), value=500, min_value=400, max_value=800, step=10,
        )
        min_decay_fraction = st.slider(
            t("min_decay_fraction", lang), 0.0, 1.0, 0.63, 0.01,
        )
        min_r_squared = st.slider(
            t("min_r_squared", lang), 0.0, 1.0, 0.70, 0.01,
        )
        min_ach = st.number_input(
            t("min_ach", lang), value=0.05, min_value=0.01, max_value=0.5,
            step=0.01, format="%.2f",
        )
        max_ach_normal = st.number_input(
            t("max_ach_normal", lang), value=1.2, min_value=0.5, max_value=5.0,
            step=0.1, format="%.1f",
        )
        max_decay_rate = st.number_input(
            t("max_decay_rate", lang), value=500, min_value=100, max_value=2000, step=50,
        )

    params = QCParams(
        ambient_co2=float(ambient),
        min_final_co2=float(min_final_co2),
        min_decay_fraction=float(min_decay_fraction),
        min_r_squared=float(min_r_squared),
        min_ach=float(min_ach),
        max_ach_normal=float(max_ach_normal),
        max_decay_rate=float(max_decay_rate),
    )

    # Data filters — only when data is loaded
    if st.session_state.df is not None:
        df = st.session_state.df
        st.divider()

        all_houses = sorted(df["HouseNo"].unique().tolist())
        if st.session_state.selected_houses is None:
            st.session_state.selected_houses = all_houses

        selected_houses = st.multiselect(
            t("building_filter", lang),
            options=all_houses,
            default=[h for h in st.session_state.selected_houses if h in all_houses],
        )
        st.session_state.selected_houses = selected_houses

        min_date = df["Date"].min()
        max_date = df["Date"].max()
        date_val = st.date_input(
            t("date_filter", lang),
            value=(
                st.session_state.date_start or min_date,
                st.session_state.date_end or max_date,
            ),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_val, (list, tuple)) and len(date_val) == 2:
            st.session_state.date_start, st.session_state.date_end = date_val

        # Re-run button when results already exist
        if st.session_state.results is not None:
            st.divider()
            if st.button(t("rerun_analysis", lang), use_container_width=True):
                with st.spinner(t("analysis_running", lang)):
                    results, rejected = run_analysis(df, params)
                st.session_state.results = results
                st.session_state.rejected = rejected
                st.rerun()

# Make params available to child pages via session state
st.session_state._params = params

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "upload":
    render_upload_page(lang)
elif page == "dashboard":
    render_dashboard(lang)
elif page == "export":
    render_export_page(lang)
