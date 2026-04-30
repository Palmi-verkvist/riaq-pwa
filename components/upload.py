import io

import pandas as pd
import streamlit as st

from analysis.decay_engine import normalise_dataframe, run_analysis
from translations import t

_REQUIRED_RAW = {"HouseNo.", "dtm", "co2, ppm"}


def _load_csv(uploaded_file) -> tuple[pd.DataFrame | None, str | None]:
    """Try utf-8 then latin-1. Returns (df, error_key)."""
    for enc in ("utf-8", "latin-1"):
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=enc, low_memory=False)
            df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
            df = df.dropna(subset=[c for c in _REQUIRED_RAW if c in df.columns])
            return df, None
        except UnicodeDecodeError:
            continue
        except Exception:
            return None, "upload_error"
    return None, "upload_error"


def _column_mapping_ui(raw_df: pd.DataFrame, lang: str) -> dict[str, str] | None:
    """
    Show dropdowns so the user can map their columns to required names.
    Returns a rename dict {their_col: our_name}, or None if auto-detected.
    """
    if _REQUIRED_RAW.issubset(set(raw_df.columns)):
        return None  # auto-detected — no mapping needed

    st.warning(t("column_map_info", lang))
    cols = list(raw_df.columns)
    rename = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        rename[st.selectbox(t("map_house", lang), cols, key="map_house")] = "HouseNo."
    with col2:
        rename[st.selectbox(t("map_datetime", lang), cols, key="map_dtm")] = "dtm"
    with col3:
        rename[st.selectbox(t("map_co2", lang), cols, key="map_co2")] = "co2, ppm"

    return rename  # {user_col: required_name}


def render_upload_page(lang: str) -> None:
    st.header(t("upload_title", lang))

    uploaded = st.file_uploader(
        t("upload_prompt", lang),
        type=["csv"],
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.session_state.df = None
        st.session_state.results = None
        st.session_state.rejected = None
        return

    # Load
    raw_df, err = _load_csv(uploaded)
    if err or raw_df is None:
        st.error(t("upload_error", lang))
        return

    # Column mapping
    rename = _column_mapping_ui(raw_df, lang)
    if rename is not None:
        # User is mapping manually — apply rename so required cols exist
        raw_df = raw_df.rename(columns=rename)
        missing = _REQUIRED_RAW - set(raw_df.columns)
        if missing:
            st.error(t("missing_columns", lang) + ", ".join(missing))
            return

    # Normalise
    try:
        df = normalise_dataframe(raw_df)
    except ValueError as exc:
        st.error(str(exc))
        return

    # Cache normalised df (re-used by dashboard)
    # Only reset results if the file changed
    if (
        st.session_state.df is None
        or len(df) != len(st.session_state.df)
    ):
        st.session_state.df = df
        st.session_state.results = None
        st.session_state.rejected = None
        st.session_state.selected_houses = None
        st.session_state.date_start = None
        st.session_state.date_end = None

    # ── Preview ───────────────────────────────────────────────────────────────
    st.subheader(t("preview_title", lang))
    st.caption(t("preview_rows", lang))
    st.dataframe(
        raw_df.head(10),
        use_container_width=True,
        hide_index=True,
    )

    # ── Dataset summary ───────────────────────────────────────────────────────
    st.subheader(t("dataset_summary_title", lang))
    c1, c2, c3 = st.columns(3)
    c1.metric(t("total_records", lang), f"{len(df):,}")
    c2.metric(t("buildings_detected", lang), df["HouseNo"].nunique())
    c3.metric(
        t("date_range", lang),
        f"{df['Date'].min()} → {df['Date'].max()}",
    )

    st.divider()

    # ── Run analysis ──────────────────────────────────────────────────────────
    if st.button(t("run_analysis", lang), type="primary", use_container_width=False):
        params = st.session_state.get("_params")
        with st.spinner(t("analysis_running", lang)):
            results, rejected = run_analysis(df, params)
        st.session_state.results = results
        st.session_state.rejected = rejected
        st.success(t("analysis_done", lang))

    # ── Results summary (shown after analysis) ────────────────────────────────
    if st.session_state.results is not None:
        results = st.session_state.results
        rejected = st.session_state.rejected
        total = len(results) + len(rejected)

        st.subheader(t("event_count", lang))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t("accepted", lang), len(results))
        m2.metric(t("rejected_label", lang), len(rejected))
        m3.metric(
            t("pct_accepted", lang),
            f"{len(results)/total*100:.1f}%" if total else "—",
        )
        m4.metric(t("purge_events", lang), int(results["IsPurge"].sum()) if len(results) else 0)

        if st.button(t("navigate_dashboard", lang)):
            st.session_state.page = "dashboard"
            st.rerun()
