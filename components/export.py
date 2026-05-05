import io

import pandas as pd
import streamlit as st

from translations import t
from utils.pdf_export import generate_pdf
from utils.ui import render_footer


def _to_excel(results_df: pd.DataFrame, rejected_df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        results_df.to_excel(writer, sheet_name="Results", index=False)
        rejected_df.to_excel(writer, sheet_name="Rejected", index=False)
    return buf.getvalue()


def render_export_page(lang: str) -> None:
    st.header(t("export_title", lang))

    if st.session_state.results is None:
        st.info(t("no_results", lang))
        render_footer()
        return

    results  = st.session_state.results
    rejected = st.session_state.rejected
    df       = st.session_state.df
    params   = st.session_state.get("_params")

    # ── Excel ─────────────────────────────────────────────────────────────────
    st.subheader("Excel")
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label=t("download_results", lang),
            data=_to_excel(results, rejected),
            file_name="riaq_ach_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            label=t("download_rejected", lang),
            data=rejected.to_csv(index=False).encode("utf-8"),
            file_name="riaq_rejected_events.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()

    # ── PDF — single button: generates and downloads in one click ─────────────
    st.subheader("PDF")

    with st.spinner(t("pdf_generating", lang)):
        try:
            pdf_bytes = generate_pdf(results, rejected, df, params, lang)
        except RuntimeError as exc:
            st.error(str(exc))
            render_footer()
            return

    st.download_button(
        label=t("pdf_download", lang),
        data=pdf_bytes,
        file_name="riaq_ventilation_report.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )

    render_footer()
