"""VIETLAB NEXUS V9.1 — Streamlit Community Cloud, chỉ dành cho demo.
Không dùng để xử lý dữ liệu khách hàng thật: localStorage của HTML không chia sẻ được
cho nhiều người dùng, không cung cấp xác thực hoặc kho hồ sơ máy chủ.
"""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "vietlab_nexus_v9_1.html"
st.set_page_config(page_title="VIETLAB NEXUS V9.1 — Demo", page_icon="🧪", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>.block-container{max-width:100%!important;padding:0.4rem 0.65rem 1rem!important}
[data-testid='stHeader']{background:transparent!important}iframe{border:0!important}</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### VIETLAB NEXUS V9.1")
    st.caption("Hợp đồng · Lịch quan trắc · Kho 5 phòng · Cảnh báo quá hạn")
    st.warning("BẢN DEMO: Dữ liệu nằm trong trình duyệt, không chia sẻ giữa nhân viên. Không nhập dữ liệu thực.")
if not HTML_FILE.exists():
    st.error(f"Thiếu tệp {HTML_FILE.name}. Vui lòng upload đầy đủ gói mã nguồn.")
    st.stop()
components.html(HTML_FILE.read_text(encoding="utf-8"), height=1900, scrolling=True)
