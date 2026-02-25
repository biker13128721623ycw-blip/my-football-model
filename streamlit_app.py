import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
import time

# --- 1. 专家级 UI 配置 ---
st.set_page_config(page_title="博彩专家-精准追踪系统", page_icon="🎯", layout="wide")

# 自定义样式
st.markdown("""
    <style>
    .stCheckbox { background-color: #1e2130; padding: 10px; border-radius: 5px; margin: 2px 0; }
    .reportview-container { background: #0e1117; }
    .predict-card { border: 2px solid #4a4e69; padding: 20px; border-radius: 15px; background: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心数学模型 ---
def calculate_metrics(minute, h_da, a_da, h_sot, a_sot, odds):
    if minute >= 90: return 0.0, 0.0
    time_rem = max(0.01, (95 - minute) / 95)
    # 专家权重公式：DA权重0.05，SOT权重0.15
    lambda_val = ((h_da + a_da) * 0.055 + (h_sot + a_sot) * 0.145) * time_rem
    prob = (1 - poisson.pmf(0, lambda_val)) * 100
    ev = (prob / 100 * odds) - 1 if odds > 0 else 0
    return round(prob, 2), round(ev, 2), round(lambda_val, 3)

# --- 3. 侧边栏设置 ---
with st.sidebar:
    st.header("🔑 接入设置")
    api_key = st.text_input("RapidAPI Key", type="password")
    st.markdown("---")
    st.subheader("📊 赔率参考")
    ref_odds = st.number_input("即时赔率 (例如大0.5)", value=1.85, step=0.05)
    st.info("提示：勾选下方的比赛进入『深度监控区』")

# --- 4. 数据抓取逻辑 ---
@st.cache_data(ttl=60)
def get_all_live_fixtures(key):
    if not key: return []
    url = "https://api-football-v1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        res = requests.get(url, headers=headers, params={"live": "all"}, timeout=10)
        return res.json().get('response', [])
    except:
        return []

# --- 5. 主界面布局 ---
st.title("🎯 精准追踪：手动筛选预测模式")

if not api_key:
    st.warning("👈 请先在左侧输入 API Key。")
else:
    live_games = get_all_live_fixtures(api_key)
    
    if not live_games:
        st.info("📡 正在搜索实时比赛... 若长时间无数据请检查 Key 或当前是否有球赛。")
    else:
        # 第一部分：比赛勾选池
        st.subheader("第一步：从实时比赛池中勾选目标 (下半场场次)")
        
        selected_fixtures = []
        
        # 建立网格展示勾选框
        cols = st.columns(3)
        for idx, game in enumerate(live_games):
            elapsed = game['fixture']['status']['elapsed']
            home = game['teams']['home']['name']
            away = game['teams']['away']['name']
            score = f"{game['goals']['home']}-{game['goals']['away']}"
            
            # 仅显示 40 分钟后的比赛方便筛选
            if elapsed >= 40:
                label = f"{elapsed}' | {home} {score} {away}"
                with cols[idx % 3]:
                    if st.checkbox(label, key=f"check_{game['fixture']['id']}"):
                        selected_fixtures.append(game)

        st.markdown("---")

        # 第二部分：深度预测区
        st.subheader("第二步：已选比赛实时预测 (AI 分析中)")
        
        if not selected_fixtures:
            st.write("⬆️ 请在上方勾选您想要预测的比赛。")
        else:
            for game in selected_fixtures:
                with st.container():
                    # 提取统计数据
                    stats_list = game.get('statistics', [])
                    h_da, a_da, h_sot, a_sot = 0, 0, 0, 0
                    if stats_list:
                        # 简单提取逻辑 (API数据结构映射)
                        for team_stat in stats_list:
                            s_dict = {s['type']: s['value'] for s in team_stat['statistics']}
                            if team_stat['team']['name'] == game['teams']['home']['name']:
                                h_da = s_dict.get('Dangerous Attacks', 0) or 0
                                h_sot = s_dict.get('Shots on Target', 0) or 0
                            else:
                                a_da = s_dict.get('Dangerous Attacks', 0) or 0
                                a_sot = s_dict.get('Shots on Target', 0) or 0

                    elapsed = game['fixture']['status']['elapsed']
                    prob, ev, lam = calculate_metrics(elapsed, h_da, a_da, h_sot, a_sot, ref_odds)

                    # UI 展示卡片
                    st.markdown(f"""
                    <div class="predict-card">
                        <table style="width:100%">
                            <tr>
                                <td style="width:40%"><h3>{game['teams']['home']['name']} vs {game['teams']['away']['name']}</h3></td>
                                <td style="text-align:center"><h4>比分: {game['goals']['home']}-{game['goals']['away']} | 时间: {elapsed}'</h4></td>
                                <td style="text-align:right"><h2 style="color:{'#00ff00' if ev > 0.1 else '#ffffff'}">{prob}% 进球率</h2></td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 指标条
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("危险进攻 (DA)", f"{h_da + a_da}")
                    c2.metric("射正 (SOT)", f"{h_sot + a_sot}")
                    c3.metric("期望进球 (λ)", lam)
                    c4.metric("期望价值 (EV)", ev, delta=f"{int(ev*100)}%", delta_color="normal")
                    st.markdown("<br>", unsafe_allow_html=True)

# 底部说明
st.caption(f"最后刷新: {time.strftime('%H:%M:%S')} | 勾选模式已激活")

