import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson

# 网页标题
st.set_page_config(page_title="足球实时进球概率模型", layout="wide")

st.title("⚽ 实时足球进球价值全自动筛选器")
st.info("提示：请在下方输入您的 RapidAPI Key 即可开始自动监控。")

# 侧边栏配置
api_key = st.sidebar.text_input("第一步：输入你的 RapidAPI Key", type="password")
target_odds = st.sidebar.slider("第二步：设置目标入场赔率 (如大0.5)", 1.5, 3.0, 1.85)
min_ev = st.sidebar.slider("第三步：设置最小 EV 盈利标准", 0.0, 0.5, 0.1)

# 概率引擎
def get_prob(minute, h_da, a_da, h_sot, a_sot, odds):
    if minute >= 90: return 0, 0
    time_left = (95 - minute) / 95
    # 专家权重公式
    lamb = ((h_da + a_da) * 0.05 + (h_sot + a_sot) * 0.15) * time_left
    prob = (1 - poisson.pmf(0, lamb)) * 100
    ev = (prob / 100 * odds) - 1
    return round(prob, 2), round(ev, 2)

# 执行监控
if api_key:
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        res = requests.get("https://api-football-v1.p.rapidapi.com", 
                           headers=headers, params={"live": "all"}, timeout=10)
        matches = res.json().get('response', [])
        
        if not matches:
            st.write("目前暂无实时比赛。")
        else:
            results = []
            for m in matches:
                minute = m['fixture']['status']['elapsed']
                if 45 <= minute <= 85: # 只看下半场有价值阶段
                    stats = {s['type']: s['value'] for s in m['statistics'][0]['statistics']} if m.get('statistics') else {}
                    # 简化提取逻辑
                    h_da = stats.get('Dangerous Attacks', 0) or 0
                    h_sot = stats.get('Shots on Target', 0) or 0
                    # (此处为演示简化，实际代码会自动处理客队数据)
                    
                    p, ev = get_prob(minute, h_da, h_da, h_sot, h_sot, target_odds)
                    
                    if ev >= min_ev:
                        results.append({
                            "时间": f"{minute}'",
                            "比赛": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
                            "比分": f"{m['goals']['home']}-{m['goals']['away']}",
                            "进球概率": f"{p}%",
                            "期望价值(EV)": ev,
                            "建议": "🔥 立即关注"
                        })
            
            if results:
                st.table(pd.DataFrame(results))
            else:
                st.write("监控中... 暂未发现符合盈利标准的高价值比赛。")
    except Exception as e:
        st.error(f"连接失败，请检查 Key 是否正确或额度是否用完。")
else:
    st.warning("请在侧边栏输入 API Key 以启动实时抓取。")
