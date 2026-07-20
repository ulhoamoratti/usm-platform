import streamlit as st

from modules import audiencias, radar, subsidios

st.set_page_config(page_title="USM Platform", page_icon="⚖️", layout="wide")

st.sidebar.title("USM Platform")
modulo = st.sidebar.radio(
    "Módulos",
    options=[
        "Conferência de Audiências",
        "Conferência de Subsídios",
        "Radar Processual",
    ],
)
st.sidebar.divider()
st.sidebar.caption("Ecossistema de Inteligência Jurídica")

st.title("USM Platform")

if modulo == "Conferência de Audiências":
    audiencias.renderizar()
elif modulo == "Conferência de Subsídios":
    subsidios.renderizar()
elif modulo == "Radar Processual":
    radar.renderizar()
