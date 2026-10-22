import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="VietLab Nexus", layout="wide")

with open("vietlab_nexus_v8_1_worklist.html", "r", encoding="utf-8") as f:
    html_data = f.read()

components.html(html_data, height=1000, scrolling=True)
