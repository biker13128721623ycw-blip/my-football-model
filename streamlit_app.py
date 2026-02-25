
import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson
import time

# --- 页面基础设置 ---
st.set_page_config(page_title="AI 进球预测实战版", layout="wide")

# --- 核心预测算法 ---
def calculate_metrics(minute, h_da, a_da, h_sot, a_sot, odds):
    if minute >= 90: return 0.0, 0.0
    time_ratio = (95 - minute) / 95
    # 专家公式：λ = (危险进攻*0.05 + 射正*0.15) * 时间系数
    lamb = ((h_da + a_da) * 0.05 + (h_sot + a_sot) * 0.15) * time_ratio
    prob = (1 - poisson.pmf(0, lamb)) * 100
    ev = (prob / 100 * odds) - 1 if odds > 0 else 0
    return round(prob, 2), round(ev, 2)

# --- 侧边栏：API 控制 ---
st.sidebar.header("🔑 系统激活")
api_key = st.sidebar.text_input("输入 RapidAPI Key", type="password")
market_odds = st.sidebar.number_input("市场赔率基准", value=1.85, step=0.05)

# --- 主逻辑 ---
st.title("⚽ 足球实时预测终端 (V7.0 修复版)")

if not api_key:
    st.warning("👈 请先在左侧输入您的 API Key。")
    st.info("💡 如果你还没有 Key，请去 RapidAPI 订阅 API-Football (Free Plan)。")
else:
    # 尝试获取数据
    url = "https://api-football-v1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    
    with st.spinner('正在同步数据...'):
        try:
            response = requests.get(url, headers=headers, params={"live": "all"}, timeout=10)
            res_data = response.json()
            
            # 调试：如果还是没列表，展开这个可以看到 API 给回了什么
            with st.expander("🛠 API 原始数据诊断 (如果看不到球队请点开这里)"):
                st.write(res_data)

            fixtures = res_data.get('response', [])

            if not fixtures:
                st.error("📡 已连接 API，但当前全球暂无进行中的实时比赛。")
            else:
                st.success(f"✅ 成功提取到 {len(fixtures)} 场比赛！")
                
                # 建立选择字典
                game_dict = {}
                for f in fixtures:
                    try:
                        h = f['teams']['home']['name']
                        a = f['teams']['away']['name']
                        m = f['fixture']['status']['elapsed']
                        score = f"{f['goals']['home']}-{f['goals']['away']}"
                        label = f"{m}' | {h} vs {a} ({score})"
                        game_dict[label] = f
                    except: continue
                
                # 下拉选择框
                selected_labels = st.multiselect("🔍 搜索并选择您要预测的比赛：", list(game_dict.keys()))

                if selected_labels:
                    for label in selected_labels:
                        match = game_dict[label]
                        # 提取统计 (DA/SOT)
                        h_da, a_da, h_sot, a_sot = 0, 0, 0, 0
                        stats = match.get('statistics', [])
                        if stats:
                            for s_grp in stats:
                                s_dict = {s['type']: s['value'] for s in s_grp['statistics']}
                                if s_grp['team']['name'] == match['teams']['home']['name']:
                                    h_da, h_sot = s_dict.get('Dangerous Attacks', 0) or 0, s_dict.get('Shots on Target', 0) or 0
                                else:
                                    a_da, a_sot = s_dict.get('Dangerous Attacks', 0) or 0, s_dict.get('Shots on Target', 0) or 0
                        
                        elapsed = match['fixture']['status']['elapsed']
                        p, ev = calculate_metrics(elapsed, h_da, a_da, h_sot, a_sot, market_odds)
                        
                        # 显示结果
                        st.divider()
                        col1, col2 = st.columns([2,1])
                        with col1:
                            st.subheader(label)
                            st.write(f"📊 进攻压力: DA({h_da+a_da}) | SOT({h_sot+a_sot})")
                        with col2:
                            st.metric("预计进球率", f"{p}%")
                            st.metric("期望价值 (EV)", f"{ev}", delta=f"{int(ev*100)}%")

        except Exception as e:
            st.error(f"❌ 运行错误: {str(e)}")

st.caption(f"最后刷新: {time.strftime('%H:%M:%S')}")

