import io

import pandas as pd
import streamlit as st

from translations import t


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
        return

    results = st.session_state.results
    rejected = st.session_state.rejected

    xlsx = _to_excel(results, rejected)

    st.download_button(
        label=t("download_results", lang),
        data=xlsx,
        file_name="riaq_ach_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.download_button(
        label=t("download_rejected", lang),
        data=rejected.to_csv(index=False).encode("utf-8"),
        file_name="riaq_rejected_events.csv",
        mime="text/csv",
        use_container_width=True,
    )
