import streamlit as st

st.set_page_config(
    page_title="USM Platform",
    page_icon="⚖️",
    layout="wide",
)

st.sidebar.title("USM Platform")

modulo = st.sidebar.radio(
    "Módulos",
    [
        "Conferência de Audiências",
        "Conferência de Subsídios",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Ecossistema de Inteligência Jurídica")

st.title("USM Platform")

if modulo == "Conferência de Audiências":
    from modules.audiencias import renderizar
    renderizar()

elif modulo == "Conferência de Subsídios":
    from modules.subsidios import renderizar
    renderizar()
