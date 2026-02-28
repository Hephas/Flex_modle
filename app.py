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
    EL_HT = st.number_input("EL-HT 電解液進入換熱前高溫 (°C)", value=55.0, step=0.5)
with col2:
    HR_LT = st.number_input("HR-LT 熱回收冷水溫度 (°C)", value=35.0, step=1.0)
with col3:
    EL_PF = st.number_input("EL-PF 當前電解液流量 (LPM)", value=100.0, step=5.0)
    current_HR_PF = st.number_input("HR-PF 當前換熱幫浦流量 (LPM)", value=50.0, step=5.0)

st.markdown("---")

# ==========================================
# 第二區：控制模型運算結果 (使用側邊欄的 ε 進行預測)
# ==========================================
def predict_control_flow(EL_PWR, EL_HT, HR_LT, max_power, T_min, PF_min, PF_max, epsilon, eff_low, eff_mid, eff_high):
    if EL_HT < T_min:
        return 0.0, f"溫度過低 (< {T_min}°C)，強制關閉幫浦保護系統。", 0.0
    if (EL_HT - HR_LT) <= 0:
        return PF_max, "錯誤：冷水溫度高於電解液，無法冷卻！", 0.0

    load_ratio = EL_PWR / max_power
    if load_ratio <= 0.30:
        energy_req = eff_low
    elif load_ratio <= 0.60:
        energy_req = eff_mid
    else:
        energy_req = eff_high

    efficiency = 3.54 / energy_req
    Q_load = EL_PWR * (1.0 - efficiency) # 理論產生的廢熱

    # 使用設定的 epsilon 計算理想冷卻流量
    ideal_flow = (60.0 * Q_load) / (4.18 * epsilon * (EL_HT - HR_LT))
    final_flow = max(PF_min, min(ideal_flow, PF_max))
    
    if ideal_flow < PF_min:
        msg = f"⚠️ 冷卻過剩警告！理論只需 {ideal_flow:.1f} LPM。給定最低 {PF_min} LPM 將導致系統降溫。"
    elif ideal_flow > PF_max:
        msg = f"⚠️ 散熱不足警告！理論需 {ideal_flow:.1f} LPM。已達最大流量極限。"
    else:
        msg = f"✅ 正常控溫中。理論與輸出流量皆為: {ideal_flow:.1f} LPM。"

    return final_flow, msg, Q_load

target_flow, msg, q_load = predict_control_flow(
    EL_PWR, EL_HT, HR_LT, max_power, T_min, PF_min, PF_max, 
    epsilon_setting, eff_low, eff_mid, eff_high
)

st.header("🤖 模型預測與控制指令")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("預測應產生的廢熱 (Q_load)", f"{q_load:.1f} kW")
metric_col2.metric("建議下一步換熱流量 (HR-PF)", f"{target_flow:.1f} LPM")
st.info(f"系統診斷: {msg}")

st.markdown("---")

# ==========================================
# 第三區：事後效能診斷 (輸入最後的實際溫度)
# ==========================================
st.header("🔍 熱交換器實測效能診斷 (事後驗證)")
st.caption("請輸入流出熱交換器後的最終實際溫度，以計算真實的熱交換狀態。")

diag_col1, diag_col2 = st.columns(2)
with diag_col1:
    EL_LT = st.number_input("EL-LT 換熱後回電解槽低溫 (°C)", value=53.5, step=0.5)
with diag_col2:
    HR_HT = st.number_input("HR-HT 換熱後熱回收高溫 (°C)", value=48.0, step=0.5)

# 熱力學真實數據計算
Cp_w = 4.18  # 比熱 (kJ/kg.K)
# 熱容量率 (kW/K)
C_hot = (EL_PF / 60.0) * Cp_w
C_cold = (current_HR_PF / 60.0) * Cp_w

# 1. 電解槽實際被帶走的熱量 (熱側失去的熱)
Q_hot_removed = C_hot * (EL_HT - EL_LT)

# 2. 熱回收實際獲得的熱量 (冷側得到的熱)
Q_cold_gained = C_cold * (HR_HT - HR_LT)

# 3. 計算實際換熱效能 ε (基於冷水側實際獲得的熱量與最大可能換熱潛力)
C_min = min(C_hot, C_cold)
max_possible_heat = C_min * (EL_HT - HR_LT)
actual_epsilon = (Q_cold_gained / max_possible_heat) if max_possible_heat > 0 else 0.0

# 顯示診斷結果
res_col1, res_col2, res_col3 = st.columns(3)
res_col1.metric("電解側實際被帶走熱量", f"{Q_hot_removed:.1f} kW", help="這是電解液流經換熱器失去的熱量")
res_col2.metric("熱回收實際獲得熱量", f"{Q_cold_gained:.1f} kW", help="這是冷卻水流經換熱器得到的熱量")
res_col3.metric("實測換熱器效能 (ε)", f"{actual_epsilon*100:.1f} %", delta=f"與左側設定差異: {(actual_epsilon - epsilon_setting)*100:.1f} %", delta_color="off")

st.caption("💡 研發夥伴提示：在理想狀態下，電解側失去的熱量應該接近熱回收獲得的熱量。如果兩者落差很大，代表熱交換器或管路有嚴重的環境散熱。此外，您可以將算出的『實測效能』更新到左側的滑桿中，讓下一次的預測更精準！")
