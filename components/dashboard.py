import streamlit as st

from components.charts import (
    plot_ach_by_building,
    plot_ach_distribution,
    plot_ach_vs_decay_rate,
    plot_co2_timeline,
)
from translations import t
from utils.ui import render_footer


def _filtered_results(lang: str):
    """Return results filtered by current sidebar selections."""
    results = st.session_state.results
    df = st.session_state.df

    selected = st.session_state.get("selected_houses") or list(results["HouseNo"].unique())
    date_start = st.session_state.get("date_start")
    date_end = st.session_state.get("date_end")

    filtered = results[results["HouseNo"].isin(selected)].copy()
    if date_start and date_end:
        filtered = filtered[
            (filtered["Date"] >= date_start) & (filtered["Date"] <= date_end)
        ]

    filtered_df = df[df["HouseNo"].isin(selected)].copy()
    if date_start and date_end:
        filtered_df = filtered_df[
            (filtered_df["Date"] >= date_start) & (filtered_df["Date"] <= date_end)
        ]

    return filtered, filtered_df


def render_dashboard(lang: str) -> None:
    if st.session_state.results is None or len(st.session_state.results) == 0:
        st.info(t("no_results", lang))
        render_footer()
        return

    params = st.session_state.get("_params")
    results, df = _filtered_results(lang)

    if results.empty:
        st.warning(t("no_data", lang))
        render_footer()
        return

    st.header(t("dashboard_title", lang))

    # ── KPI row ───────────────────────────────────────────────────────────────
    total_all = len(st.session_state.results) + len(st.session_state.rejected)
    pct = len(results) / total_all * 100 if total_all else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("total_buildings", lang), results["HouseNo"].nunique())
    k2.metric(t("mean_ach", lang), f"{results['ACH_per_hour'].mean():.3f} h⁻¹")
    k3.metric(t("pct_accepted", lang), f"{pct:.1f}%")
    k4.metric(
        t("date_range", lang),
        f"{results['Date'].min()} → {results['Date'].max()}",
    )

    st.divider()

    # ── Charts 1 & 2 ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(t("ach_distribution", lang))
        st.plotly_chart(
            plot_ach_distribution(results, params, lang),
            use_container_width=True,
        )

    with col_right:
        st.subheader(t("ach_by_building", lang))
        st.plotly_chart(
            plot_ach_by_building(results, params, lang),
            use_container_width=True,
        )

    st.divider()

    # ── Chart 3 — CO2 Timeline ────────────────────────────────────────────────
    st.subheader(t("co2_timeline", lang))
    houses = sorted(results["HouseNo"].unique().tolist())
    selected_house = st.selectbox(
        t("select_building", lang),
        options=houses,
        label_visibility="collapsed",
    )
    st.plotly_chart(
        plot_co2_timeline(df, selected_house, results, lang),
        use_container_width=True,
    )

    st.divider()

    # ── Chart 4 — ACH vs Decay Rate ───────────────────────────────────────────
    st.subheader(t("ach_vs_decay_rate", lang))
    st.plotly_chart(
        plot_ach_vs_decay_rate(results, params, lang),
        use_container_width=True,
    )

    render_footer()
