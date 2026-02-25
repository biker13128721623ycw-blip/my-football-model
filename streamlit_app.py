import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
import time

# --- [UI 界面定制] ---
st.set_page_config(page_title="足球进球 AI 核心终端", page_icon="💹", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .game-card { border: 1px solid #30363d; padding: 20px; border-radius: 12px; background: #161b22; margin-bottom: 15px; }
    .highlight-green { color: #3fb950; font-weight: bold; font-size: 24px; }
    .highlight-red { color: #f85149; font-weight: bold; }
    .stat-label { color: #8b949e; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- [数学预测模型] ---
def calculate_advanced_metrics(minute, h_da, a_da, h_sot, a_sot, odds):
    """基于泊松分布的压力指数模型"""
    if minute >= 90: return 0.0, 0.0, 0.0
    
    # 核心权重逻辑：随着比赛进行，射正(SOT)对λ的贡献权重逐渐加大
    time_remaining_ratio = (95 - minute) / 95
    # λ (期望进球率) = (危险进攻 * 0.05 + 射正 * 0.16) * 剩余时间系数
    current_lambda = ((h_da + a_da) * 0.052 + (h_sot + a_sot) * 0.155) * time_remaining_ratio
    
    # 进球概率 P(X > 0)
    prob = (1 - poisson.pmf(0, current_lambda)) * 100
    # EV (期望价值) = (概率 * 赔率) - 1
    ev = (prob / 100 * odds) - 1 if odds > 0 else 0
    
    return round(prob, 2), round(ev, 2), round(current_lambda, 3)

# --- [API 数据解析] ---
@st.cache_data(ttl=30)
def fetch_live_data(api_key):
    if not api_key: return None, "MISSING_KEY"
    url = "https://api-football-v1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        # 获取所有实时比赛
        response = requests.get(url, headers=headers, params={"live": "all"}, timeout=12)
        res_json = response.json()
        
        if "errors" in res_json and res_json["errors"]:
            return None, str(res_json["errors"])
        
        return res_json.get('response', []), None
    except Exception as e:
        return None, str(e)

# --- [主界面逻辑] ---
st.title("💹 足球实时进球 AI 价值监控终端")
st.sidebar.header("🛠 核心设置")
user_api_key = st.sidebar.text_input("RapidAPI Key", type="password", help="在此输入您的密钥以激活全球数据")
user_odds = st.sidebar.number_input("目标市场赔率 (大0.5)", value=1.85, min_value=1.01, step=0.05)
min_ev_threshold = st.sidebar.slider("最低入场 EV 标准", 0.0, 0.5, 0.1)

if not user_api_key:
    st.warning("👈 请在左侧侧边栏填入您的 API-Football Key 开启预测。")
else:
    fixtures, error = fetch_live_data(user_api_key)
    
    if error:
        st.error(f"❌ 系统诊断报错: {error}")
        st.info("💡 常见原因：Key错误、未订阅免费套餐、或 API 额度耗尽。")
    elif not fixtures:
        st.info("📡 数据连接成功。当前全球暂无进行中的实时比赛。")
    else:
        st.success(f"✅ 成功对接！当前检测到 {len(fixtures)} 场实时赛事。")
        
        # 构建可勾选的球队字典
        game_map = {}
        options_list = []
        
        for f in fixtures:
            try:
                fid = f['fixture']['id']
                h_name = f['teams']['home']['name']
                a_name = f['teams']['away']['name']
                elapsed = f['fixture']['status']['elapsed']
                goals_h = f['goals']['home'] if f['goals']['home'] is not None else 0
                goals_a = f['goals']['home'] if f['goals']['away'] is not None else 0
                
                label = f"{elapsed}' | {h_name} {goals_h}-{goals_a} {a_name}"
                game_map[label] = f
                options_list.append(label)
            except:
                continue

        # 第一步：手动筛选
        st.subheader("第一步：选择监控目标")
        selected_labels = st.multiselect("🔍 搜索并勾选您感兴趣的比赛：", options_list)
        
        st.markdown("---")
        
        # 第二步：深度预测
        st.subheader("第二步：AI 实时预测分析")
        
        if not selected_labels:
            st.write("💡 请在上方搜索框勾选比赛，系统将立即为您计算进球概率与 EV。")
        else:
            for label in selected_labels:
                match_data = game_map[label]
                
                # 统计数据解析 (防御性提取)
                h_da, a_da, h_sot, a_sot = 0, 0, 0, 0
                stats_list = match_data.get('statistics', [])
                
                for s_group in stats_list:
                    s_dict = {s['type']: s['value'] for s in s_group['statistics'] if s['value'] is not None}
                    if s_group['team']['id'] == match_data['teams']['home']['id']:
                        h_da = s_dict.get('Dangerous Attacks', 0)
                        h_sot = s_dict.get('Shots on Target', 0)
                    else:
                        a_da = s_dict.get('Dangerous Attacks', 0)
                        a_sot = s_dict.get('Shots on Target', 0)

                elapsed = match_data['fixture']['status']['elapsed']
                prob, ev, lam = calculate_advanced_metrics(elapsed, h_da, a_da, h_sot, a_sot, user_odds)

                # 展示卡片
                st.markdown(f"""
                <div class="game-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span class="stat-label">比赛场次</span>
                            <h3 style="margin-top:0;">{label}</h3>
                        </div>
                        <div style="text-align: right;">
                            <span class="stat-label">预计进球率</span>
                            <div class="highlight-green">{prob}%</div>
                        </div>
                    </div>
                    <hr style="border: 0.1px solid #30363d; margin: 15px 0;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <span class="stat-label">进攻压力 (DA/SOT)</span><br>
                            <b>{h_da + a_da} / {h_sot + a_sot}</b>
                        </div>
                        <div>
                            <span class="stat-label">期望进球 (λ)</span><br>
                            <b>{lam}</b>
                        </div>
                        <div>
                            <span class="stat-label">期望价值 (EV)</span><br>
                            <span style="color: {'#3fb950' if ev >= min_ev_threshold else '#f85149'}; font-weight:bold;">{ev}</span>
                        </div>
                        <div style="text-align: right;">
                            <span class="stat-label">操作建议</span><br>
                            <b>{'🔥 立即入场' if ev >= min_ev_threshold else '⏳ 等待价值'}</b>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.caption(f"系统全自动运行中 | 最后刷新: {time.strftime('%H:%M:%S')} | 数据源: API-Football")

