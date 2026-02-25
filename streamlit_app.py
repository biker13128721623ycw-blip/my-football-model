import streamlit as st
import requests
import pandas as pd
from scipy.stats import poisson

st.set_page_config(page_title="足球价值追踪器", layout="wide")

# --- 1. 核心模型与API抓取 ---
def get_live_data(key):
    if not key: return None, "未输入 API Key"
    url = "https://api-football-v1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers, params={"live": "all"}, timeout=15)
        res_json = response.json()
        # 错误诊断
        if "errors" in res_json and res_json["errors"]:
            return None, f"API 报错: {res_json['errors']}"
        return res_json.get('response', []), None
    except Exception as e:
        return None, f"网络连接错误: {str(e)}"

# --- 2. 界面与交互 ---
st.title("🎯 足球预测终端")
api_key = st.sidebar.text_input("RapidAPI Key", type="password")
market_odds = st.sidebar.number_input("实时赔率 (大0.5)", value=1.85, step=0.05)

if not api_key:
    st.warning("请在侧边栏填入 API Key。")
else:
    fixtures, error_msg = get_live_data(api_key)
    
    if error_msg:
        st.error(f"❌ 诊断: {error_msg}")
        st.info("💡 请确保已在 [RapidAPI](https://rapidapi.com) 订阅 API-Football。")
    elif not fixtures:
        st.info("📡 正常，但目前暂无实时比赛。")
    else:
        st.success(f"✅ 连接成功！检测到 {len(fixtures)} 场比赛。")
        # 数据解析 (加入异常处理)
        options = []
        for f in fixtures:
            try:
                home = f['teams']['home']['name']
                away = f['teams']['away']['name']
                min_ = f['fixture']['status']['elapsed']
                score = f"{f['goals']['home']}-{f['goals']['away']}"
                options.append({"label": f"{min_}' | {home} vs {away} ({score})", "data": f})
            except KeyError: continue
        
        selected = st.multiselect("选择比赛", [o['label'] for o in options])
        # ... (后续分析逻辑同上)

