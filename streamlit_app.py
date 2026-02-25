import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
import time

# --- 1. 专家级 UI 配置 ---
st.set_page_config(
    page_title="足球进球 AI 实时预测 - 博彩专家版",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式：美化表格和卡片
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #4a4e69; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .ev-high { color: #00ff00; font-weight: bold; }
    .ev-low { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心数学逻辑 ---
def calculate_ev(minute, h_da, a_da, h_sot, a_sot, odds):
    if minute >= 90: return 0.0, 0.0
    time_rem_ratio = max(0.01, (95 - minute) / 95)
    # 专家权重逻辑
    lambda_rem = ((h_da + a_da) * 0.052 + (h_sot + a_sot) * 0.14) * time_rem_ratio
    prob = (1 - poisson.pmf(0, lambda_rem)) * 100
    ev = (prob / 100 * odds) - 1 if odds > 0 else 0
    return round(prob, 2), round(ev, 2)

# --- 3. 侧边栏设置 ---
with st.sidebar:
    st.image("https://img.icons8.com", width=80)
    st.header("⚙️ 监控中心")
    api_key = st.text_input("RapidAPI Key", type="password", help="从 RapidAPI 获取的 API-Football 密钥")
    
    st.markdown("---")
    st.subheader("🎯 投资参数")
    target_odds = st.slider("目标实时赔率", 1.2, 3.5, 1.85, 0.05)
    min_ev = st.slider("最小盈利标准 (EV)", 0.0, 0.5, 0.15, 0.01)
    
    st.markdown("---")
    st.write("🔄 **自动刷新**：Streamlit 默认交互即刷新")
    if st.button("🚀 强制刷新数据"):
        st.rerun()

# --- 4. 主界面布局 ---
st.title("📊 足球下半场进球 AI 实时价值监控")

# 顶部状态栏
c1, c2, c3 = st.columns(3)
with c1:
    st.info("📡 **系统状态**：正在监控全球实时赛事")
with c2:
    st.success(f"📈 **当前标准**：EV > {min_ev}")
with c3:
    st.metric("目标赔率基准", f"{target_odds}")

# --- 5. 数据抓取与展示 ---
if not api_key:
    st.warning("👈 请先在左侧侧边栏填入您的 API Key 以启动实时数据。")
else:
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    
    try:
        res = requests.get("https://api-football-v1.p.rapidapi.com", 
                           headers=headers, params={"live": "all"}, timeout=15)
        data = res.json().get('response', [])

        if not data:
            st.info("🕒 当前暂无正在进行的比赛。")
        else:
            high_val_games = []
            all_games = []

            for match in data:
                elapsed = match['fixture']['status']['elapsed']
                # 核心筛选范围：45-88 分钟
                if 45 <= elapsed <= 88:
                    stats_list = match.get('statistics', [])
                    if not stats_list: continue
                    
                    # 提取统计
                    stats_map = {}
                    for team_stat in stats_list:
                        for s in team_stat['statistics']:
                            stats_map[s['type']] = stats_map.get(s['type'], 0) + (s['value'] or 0)
                    
                    da = stats_map.get('Dangerous Attacks', 0)
                    sot = stats_map.get('Shots on Target', 0)
                    prob, ev = calculate_ev(elapsed, da, 0, sot, 0, target_odds)
                    
                    game_info = {
                        "Time": f"{elapsed}'",
                        "Match": f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
                        "Score": f"{match['goals']['home']}-{match['goals']['away']}",
                        "DA": da,
                        "SOT": sot,
                        "Prob": f"{prob}%",
                        "EV": ev
                    }
                    
                    if ev >= min_ev:
                        high_val_games.append(game_info)
                    all_games.append(game_info)

            # --- 展示区域 ---
            st.subheader("🔥 高价值机会 (High Value)")
            if high_val_games:
                # 使用卡片展示最高价值的前三场
                cols = st.columns(len(high_val_games[:3]))
                for idx, game in enumerate(high_val_games[:3]):
                    with cols[idx]:
                        st.markdown(f"""
                        <div style="background-color:#1e2130; padding:20px; border-radius:10px; border-left: 5px solid #00ff00;">
                            <h4 style="margin:0;">{game['Match']}</h4>
                            <p style="color:#aaa;">比分: {game['Score']} | 时间: {game['Time']}</p>
                            <h2 style="color:#00ff00; margin:5px 0;">{game['Prob']}</h2>
                            <p style="margin:0;">期望价值 (EV): <b>{game['EV']}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.write("📋 **详细筛选列表**")
                st.table(pd.DataFrame(high_val_games))
            else:
                st.info("🔍 正在扫描全球数据，暂未发现符合 EV 标准的入场点...")

            with st.expander("🌐 查看所有进行中的比赛统计"):
                if all_games:
                    st.dataframe(pd.DataFrame(all_games), use_container_width=True)

    except Exception as e:
        st.error(f"❌ 数据请求出错，请检查 API Key 是否有效。")

st.markdown("---")
st.caption(f"🚀 数据每分钟自动同步 | 当前时间: {time.strftime('%H:%M:%S')} | 博彩专家模型 V2.0")
