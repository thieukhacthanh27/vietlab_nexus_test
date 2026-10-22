"""VietLab Nexus V8.3 — Streamlit Community Cloud DEMO wrapper.

The HTML application runs in an isolated iframe. Its localStorage/IndexedDB data
is per browser, NOT shared among employees. Use the backend pilot/production API
for real collaboration; never use this as a production LIMS.
"""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / 'vietlab_nexus_v8_1_worklist.html'

st.set_page_config(
    page_title='VIETLAB NEXUS V8.1 | Demo Streamlit',
    page_icon='🧪',
    layout='wide',
    initial_sidebar_state='collapsed',
)
st.markdown('''<style>
.block-container{max-width:100%!important;padding:0.45rem 0.7rem 1rem!important}
[data-testid="stHeader"]{background:transparent!important}
iframe{border:0!important}
</style>''', unsafe_allow_html=True)

# Sidebar supplied by Streamlit is optional. VietLab also has its own collapsible
# tool bar inside the embedded application.
with st.sidebar:
    st.markdown('### VIETLAB NEXUS V8.1')
    st.caption('Bản dùng thử từ GitHub · không chứa cơ sở dữ liệu chung')
    st.markdown('**Các tính năng:** Trang chủ thống kê · Bộ lọc ngày · Thu gọn menu · Excel / CSV / in PDF.')
    st.warning('Không nhập hồ sơ hoặc dữ liệu thử nghiệm thật. Dữ liệu HTML chỉ nằm trong trình duyệt.')

if not HTML_FILE.is_file():
    st.error('Thiếu file vietlab_nexus_v8_3_streamlit.html. Hãy tải lên đủ các tệp trong gói V8.1.')
    st.stop()

# Avoid shared st.cache_data for mutable state; HTML reads localStorage on the client.
# Large height provides an inside-app scroll while maintaining legacy desktop/mobile UI.
if hasattr(st, 'iframe'):
    st.iframe(HTML_FILE, height=1900)
else:
    components.html(HTML_FILE.read_text(encoding='utf-8'), height=1900, scrolling=True)
