import streamlit as st

st.set_page_config(page_title="AEM 電解槽熱管理模型", layout="wide")
st.title("⚡ AEM 電解系統 - 動態熱回收模擬器 (工程校準版)")

# ==========================================
# 側邊欄：硬體邊界與「經驗參數校準區」
# ==========================================
st.sidebar.header("⚙️ 系統與硬體邊界設定")
T_target = st.sidebar.number_input("目標控制溫度 (°C)", value=55.0)
T_min = st.sidebar.number_input("強制關閉幫浦溫度 (°C)", value=53.0)
PF_min = st.sidebar.number_input("幫浦最低流量 (LPM)", value=30.0)
PF_max = st.sidebar.number_input("幫浦最大流量 (LPM)", value=100.0)
max_power = st.sidebar.number_input("系統滿載功率 (kW)", value=120.0)

st.sidebar.markdown("---")
st.sidebar.header("🔧 模型校準參數 (隨實驗動態修正)")

# [維度一] 熱交換器效能修正
st.sidebar.subheader("1. 換熱器效能 (ε)")
epsilon = st.sidebar.slider(
    "板式熱交換器效能係數", 
    min_value=0.10, max_value=1.00, value=0.85, step=0.01,
    help="若發現實際降溫太慢，可能是換熱器結垢或效能不佳，請調低此數值。"
)

# [維度二] 電堆老化與發熱效率修正
st.sidebar.subheader("2. 系統能耗基準 (kWh/Nm³)")
st.sidebar.caption("若電堆老化導致廢熱增加，請調高以下數值：")
eff_low = st.sidebar.number_input("低載區間 (0-30%)", value=5.2, step=0.1)
eff_mid = st.sidebar.number_input("中載區間 (30-60%)", value=5.0, step=0.1)
eff_high = st.sidebar.number_input("高載區間 (60-100%)", value=4.8, step=0.1)

# ==========================================
# 主畫面：動態感測器輸入
# ==========================================
st.header("🎛️ 當前感測器狀態 (手動輸入模擬)")
col1, col2, col3 = st.columns(3)
with col1:
    EL_PWR = st.number_input("EL-PWR 輸入功率 (kW)", value=50.0, step=5.0)
with col2:
    EL_HT = st.number_input("EL-HT 電解液溫度 (°C)", value=55.0, step=0.5)
with col3:
    HR_LT = st.number_input("HR-LT 熱回收冷水溫度 (°C)", value=35.0, step=1.0)

st.markdown("---")

# ==========================================
# 核心熱力學演算法 (已接入動態校準參數)
# ==========================================
def calculate_hr_pf(EL_PWR, EL_HT, HR_LT, max_power, T_min, PF_min, PF_max, epsilon, eff_low, eff_mid, eff_high):
    if EL_HT < T_min:
        return 0.0, f"溫度過低 (< {T_min}°C)，強制關閉幫浦保護系統。"
    if (EL_HT - HR_LT) <= 0:
        return PF_max, "錯誤：冷水溫度高於電解液，無法冷卻！"

    # 動態讀取側邊欄的階梯效率
    load_ratio = EL_PWR / max_power
    if load_ratio <= 0.30:
        energy_req = eff_low
    elif load_ratio <= 0.60:
        energy_req = eff_mid
    else:
        energy_req = eff_high

    # 廢熱推導
    efficiency = 3.54 / energy_req
    heat_ratio = 1.0 - efficiency
    Q_load = EL_PWR * heat_ratio

    # 最佳流量計算 (Cp = 4.18, epsilon 由側邊欄動態輸入)
    ideal_flow = (60.0 * Q_load) / (4.18 * epsilon * (EL_HT - HR_LT))
    
    # 幫浦極限限制
    final_flow = max(PF_min, min(ideal_flow, PF_max))
    
    if ideal_flow < PF_min:
        msg = f"⚠️ 冷卻過剩警告！理論只需 {ideal_flow:.1f} LPM。給定最低 {PF_min} LPM 將導致系統降溫。"
    elif ideal_flow > PF_max:
        msg = f"⚠️ 散熱不足警告！理論需 {ideal_flow:.1f} LPM。已達最大流量極限。"
    else:
        msg = f"✅ 正常控溫中。理論與輸出流量皆為: {ideal_flow:.1f} LPM。"

    return final_flow, msg, Q_load, efficiency

# 執行運算
target_flow, msg, q_load, eff = calculate_hr_pf(
    EL_PWR, EL_HT, HR_LT, max_power, T_min, PF_min, PF_max, 
    epsilon, eff_low, eff_mid, eff_high
)

# ==========================================
# 顯示結果
# ==========================================
st.header("📊 模型運算結果")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("建議幫浦流量 (HR-PF)", f"{target_flow:.1f} LPM")
metric_col2.metric("預估實際廢熱", f"{q_load:.1f} kW")
metric_col3.metric("推算系統法拉第效率", f"{eff*100:.1f} %")

st.info(f"系統診斷: {msg}")
