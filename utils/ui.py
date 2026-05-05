import streamlit as st


def render_footer() -> None:
    st.markdown(
        '<div class="verkvist-footer">© VERKVIST</div>',
        unsafe_allow_html=True,
    )
