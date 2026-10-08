"""Launch: streamlit run app.py"""
import streamlit as st
from dotenv import load_dotenv

from src.utils import ROOT

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="HINO EcoPilot｜車隊協同節能決策原型", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
st.logo(str(ROOT / "assets/logo.svg"), size="large")
navigation = st.navigation([
    st.Page("pages/1_Data_Journey.py", title="資料旅程", icon=":material/account_tree:"),
    st.Page("pages/2_Fleet_Overview.py", title="車隊總覽", icon=":material/dashboard:", default=True),
    st.Page("pages/3_Trip_Explorer.py", title="行程探索", icon=":material/route:"),
    st.Page("pages/4_Driver_Eco_Coach.py", title="駕駛節能教練", icon=":material/eco:"),
    st.Page("pages/5_Manager_Action_Center.py", title="管理行動中心", icon=":material/assignment_turned_in:"),
    st.Page("pages/6_Data_Assumptions.py", title="資料與假設", icon=":material/database:"),
])
navigation.run()
