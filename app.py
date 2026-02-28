import streamlit as st

st.set_page_config(page_title="AEM 電解槽熱管理模型", layout="wide")
st.title("⚡ AEM 電解系統 - 預測控制與效能診斷雙引擎")

# ==========================================
# 側邊欄：基礎數值與模型設定 (前饋控制的基準)
# ==========================================
st.sidebar.header("⚙️ 系統常數與邊界設定")
T_target = st.sidebar.number_input("目標控制溫度 (°C)", value=55.0)
T_min = st.sidebar.number_input("強制關閉幫浦溫度 (°C)", value=53.0)
PF_min = st.sidebar.number_input("幫浦最低流量 (LPM)", value=30.0)
PF_max = st.sidebar.number_input("幫浦最大流量 (LPM)", value=100.0)
max_power = st.sidebar.number_input("系統滿載功率 (kW)", value=120.0)

st.sidebar.markdown("---")
st.sidebar.header("🔧 模型校準參數 (用於計算預測流量)")
epsilon_setting = st.sidebar.slider(
    "設定的換熱器效能 (ε)", 
    min_value=0.10, max_value=1.00, value=0.85, step=0.01,
    help="這是基礎數值，用於前饋預測幫浦的控制流量。"
)

st.sidebar.caption("AEM 能耗基準 (kWh/Nm³)")
eff_low = st.sidebar.number_input("低載區間 (0-30%)", value=5.2, step=0.1)
eff_mid = st.sidebar.number_input("中載區間 (30-60%)", value=5.0, step=0.1)
eff_high = st.sidebar.number_input("高載區間 (60-100%)", value=4.8, step=0.1)

# ==========================================
# 第一區：感測器狀態 (輸入區)
# ==========================================
st.header("🎛️ 當前感測器狀態 (運行前輸入)")
col1, col2, col3 = st.columns(3)
with col1:
    EL_PWR = st.number_input("EL-PWR 輸入功率 (kW)", value=50.0, step=5.0)
    EL_HT = st.number_input("EL-HT 電解液進入
