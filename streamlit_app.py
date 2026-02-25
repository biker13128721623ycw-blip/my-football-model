import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
import time

# --- 1. 页面配置 ---
st.set_page_config(page_title="博彩专家-终极实战终端", page_icon="💰", layout="wide")

# 自定义 CSS 提升 UI
st.markdown("""
    <style>
    .game-card { background: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 10px; }
    .metric-val { color: #58a6ff; font-size: 20px; font-weight: bold; }
    .ev-win { color: #3fb950; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心数学模型 (EV 计算器) ---
def get_model_result(minute, h_da, a_da, h_sot, a_sot, live_odds):
    if minute >= 90: return 0.0, 0.0, 0.0
    # 剩余时间占比
    time_left = max(0.01, (95 - minute) / 95)
    # 专家权重 λ 公式
    lamb = ((h_da + a_da) * 0.055 + (h_sot + a_sot) * 0.15) * time_left
    # 概率 P(X>0)
    prob = (1 - poisson.pmf(0, lamb)) * 100
    # EV = (概率 * 赔率) - 1
    ev = (prob / 100 * live_odds) - 1 if live_odds > 0 else 0
    return round(prob, 2), round(ev, 2), round(lamb, 3)

# --- 3. 侧边栏：API 密钥与赔率 ---
st.sidebar.header("🛡️ 系统控制台")
api_key = st.sidebar.text_input("RapidAPI Key (必填)", type="password")
target_odds = st.sidebar.number_input("当前市场赔率 (大0.5)", value=1.85, step=0.05)
st.sidebar.markdown("---")
st.sidebar.info("建议入场标准：\n1. 进球率 > 70%\n2. EV > 0.10")

# --- 4. 实时数据获取函数 (修复数据解析逻辑) ---
@st.cache_data(ttl=60)
def fetch_live_fixtures(key):
    if not key: return []
    url = "https://api-football-v1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        # 注意：此处必须请求 statistics 扩展包
        response = requests.get(url, headers=headers, params={"live": "all"}, timeout=12)
        return response.json().get('response', [])
    except Exception as e:
        st.error(f"网络请求失败: {e}")
        return []

# --- 5. 主程序 ---
st.title("⚽ 实时足球进球价值预测 (精准勾选模式)")

if not api_key:
    st.warning("👈 请先在左侧输入您的 API Key 以激活系统。")
else:
    data = fetch_live_fixtures(api_key)
    
    if not data:
        st.info("📡 正在扫描全球赛事... 暂无符合条件的实时比赛。")
    else:
        st.subheader("第一步：选择您要分析的比赛")
        
        # 建立比赛映射表，方便勾选
        game_options = []
        for match in data:
            m_id = match['fixture']['id']
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            minute = match['fixture']['status']['elapsed']
            score = f"{match['goals']['home']}-{match['goals']['away']}"
            game_options.append({
                "id": m_id,
                "label": f"{minute}' | {home} {score} {away}",
                "raw": match
            })
        
        # 使用多选框进行手动筛选
        selected_labels = st.multiselect("点击搜索并勾选比赛：", [g['label'] for g in game_options])
        selected_games = [g['raw'] for g in game_options if g['label'] in selected_labels]

        st.markdown("---")
        st.subheader("第二步：实时预测与期望价值 (EV)")

        if not selected_games:
            st.write("💡 请在上方搜索框内勾选感兴趣的场次开始预测。")
        else:
            for game in selected_games:
                with st.container():
                    # 解析统计数据 (关键修复点)
                    stats = game.get('statistics', [])
                    h_da, a_da, h_sot, a_sot = 0, 0, 0, 0
                    
                    if stats:
                        for s_group in stats:
                            s_dict = {s['type']: s['value'] for s in s_group['statistics']}
                            if s_group['team']['name'] == game['teams']['home']['name']:
                                h_da, h_sot = s_dict.get('Dangerous Attacks', 0) or 0, s_dict.get('Shots on Target', 0) or 0
                            else:
                                a_da, a_sot = s_dict.get('Dangerous Attacks', 0) or 0, s_dict.get('Shots on Target', 0) or 0

                    minute = game['fixture']['status']['elapsed']
                    prob, ev, lam = get_model_result(minute, h_da, a_da, h_sot, a_sot, target_odds)

                    # UI 卡片展示
                    st.markdown(f"""
                    <div class="game-card">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <h3 style="margin-bottom:0;">{game['teams']['home']['name']} vs {game['teams']['away']['name']}</h3>
                                <p style="color:#8b949e;">时间: {minute}' | 比分: {game['goals']['home']}-{game['goals']['away']}</p>
                            </div>
                            <div style="text-align: right;">
                                <div class="ev-win">{prob}% 进球率</div>
                                <div style="color:{'#3fb950' if ev > 0 else '#f85149'}">期望价值 (EV): {ev}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("总危险进攻", h_da + a_da)
                    c2.metric("总射正次数", h_sot + a_sot)
                    c3.metric("期望进球 λ", lam)
                    c4.metric("盈利空间 (ROI)", f"{int(ev*100)}%")
                    st.markdown("<hr style='border:0.5px solid #30363d'>", unsafe_allow_html=True)

st.caption(f"系统运行中 | 数据更新时间: {time.strftime('%H:%M:%S')}")

